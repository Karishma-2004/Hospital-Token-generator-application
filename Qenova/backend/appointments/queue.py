"""Queue logic shared by the REST views and the WebSocket consumer.

Queue order = the order in which patients were checked in (first come, first served),
for booked patients and walk-ins alike.
"""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from doctors.models import DoctorProfile
from .models import Appointment
from .payments import fee_for, payment_state

NEAR_THRESHOLD = 2           # "your turn is near" when this many patients (or fewer) are ahead
BOARD_WAITING_LIMIT = 6      # tokens shown per doctor on the lobby display


# ---------------------------------------------------------------- helpers
def display_name(appointment):
    if appointment.patient_id:
        p = appointment.patient
        return p.get_full_name() or p.username
    return appointment.walk_in_name or "Walk-in patient"


def doctor_name(doctor):
    return f"Dr. {doctor.user.first_name} {doctor.user.last_name}".strip()


def queue_item(a):
    """Small dict used by the receptionist and doctor screens (no QR secret in here)."""
    return {
        "id": a.id,
        "token_number": a.token_number,
        "patient_name": display_name(a),
        "is_walk_in": a.is_walk_in,
        "phone": a.walk_in_phone if a.is_walk_in else "",
        "doctor_id": a.doctor_id,
        "doctor_name": doctor_name(a.doctor),
        "appointment_time": a.appointment_time.strftime("%H:%M"),
        "status": a.status,
        "checked_in_at": a.checked_in_at.isoformat() if a.checked_in_at else None,
        "called_at": a.called_at.isoformat() if a.called_at else None,
        "fee": str(fee_for(a)),
        "payment_status": payment_state(a),
        "has_prescription": getattr(a, "prescription", None) is not None,
    }


def todays(qs=None):
    qs = Appointment.objects.all() if qs is None else qs
    return qs.filter(appointment_date=timezone.localdate())


def waiting_order(qs):
    return qs.filter(status=Appointment.STATUS_CHECKED_IN).order_by("checked_in_at", "id")


# ---------------------------------------------------------------- estimates
def average_consult_minutes(doctor):
    rows = (
        Appointment.objects.filter(
            doctor=doctor, status=Appointment.STATUS_COMPLETED,
            called_at__isnull=False, completed_at__isnull=False,
        )
        .order_by("-completed_at")
        .values_list("called_at", "completed_at")[:20]
    )
    mins = [(done - start).total_seconds() / 60 for start, done in rows]
    mins = [m for m in mins if 0.5 <= m <= 120]
    if mins:
        return max(3, round(sum(mins) / len(mins)))
    today = timezone.localdate()
    for s in doctor.schedules.all():
        if s.is_active and s.weekday == today.weekday():
            return s.slot_minutes
    return 15


def patient_queue_info(a):
    """Position and wait-time estimate for one appointment."""
    doctor = a.doctor
    day_qs = Appointment.objects.filter(doctor=doctor, appointment_date=a.appointment_date)
    current = day_qs.filter(status=Appointment.STATUS_IN_CONSULTATION).order_by("called_at").first()
    avg = average_consult_minutes(doctor)

    info = {
        "id": a.id,
        "hospital_id": a.hospital_id,
        "hospital_name": a.hospital.name,
        "doctor_name": doctor_name(doctor),
        "token_number": a.token_number,
        "status": a.status,
        "appointment_time": a.appointment_time.strftime("%H:%M"),
        "now_serving": current.token_number if current else None,
        "patients_ahead": None,
        "estimated_wait_minutes": None,
        "near": False,
        "your_turn": a.status == Appointment.STATUS_IN_CONSULTATION,
    }
    if a.status == Appointment.STATUS_CHECKED_IN:
        ref = a.checked_in_at or a.updated_at
        waiting_ahead = day_qs.filter(status=Appointment.STATUS_CHECKED_IN).filter(
            Q(checked_in_at__lt=ref) | Q(checked_in_at=ref, id__lt=a.id)
        ).count()
        remaining_current = 0
        if current:
            elapsed = (timezone.now() - current.called_at).total_seconds() / 60 if current.called_at else 0
            remaining_current = max(avg - elapsed, 1)
        ahead = waiting_ahead + (1 if current else 0)
        info["patients_ahead"] = ahead
        info["estimated_wait_minutes"] = int(round(remaining_current + waiting_ahead * avg))
        info["near"] = ahead <= NEAR_THRESHOLD
    return info


# ---------------------------------------------------------------- state changes
def check_in(a):
    a.status = Appointment.STATUS_CHECKED_IN
    a.checked_in_at = timezone.now()
    a.save(update_fields=["status", "checked_in_at", "updated_at"])


def complete(a):
    a.status = Appointment.STATUS_COMPLETED
    a.completed_at = timezone.now()
    a.save(update_fields=["status", "completed_at", "updated_at"])


@transaction.atomic
def call_next(doctor):
    """Finish whoever is inside, then call the first checked-in patient. Returns that patient or None."""
    day_qs = Appointment.objects.select_for_update().filter(
        doctor=doctor, appointment_date=timezone.localdate()
    )
    for current in list(day_qs.filter(status=Appointment.STATUS_IN_CONSULTATION)):
        complete(current)
    nxt = waiting_order(day_qs).first()
    if nxt:
        nxt.status = Appointment.STATUS_IN_CONSULTATION
        nxt.called_at = timezone.now()
        nxt.save(update_fields=["status", "called_at", "updated_at"])
    return nxt


# ---------------------------------------------------------------- live board
def board_snapshot(hospital_id):
    """Public data for the lobby display: token numbers only, no patient names."""
    today = timezone.localdate()
    doctors = (
        DoctorProfile.objects.select_related("user", "department")
        .prefetch_related("schedules")
        .filter(hospital_id=hospital_id, is_active=True, is_verified=True)
    )
    active = list(
        Appointment.objects.filter(
            hospital_id=hospital_id, appointment_date=today,
            status__in=[Appointment.STATUS_CHECKED_IN, Appointment.STATUS_IN_CONSULTATION],
        ).order_by("checked_in_at", "id")
    )
    rows = []
    for d in doctors:
        mine = [a for a in active if a.doctor_id == d.id]
        works_today = any(s.is_active and s.weekday == today.weekday() for s in d.schedules.all())
        if not mine and not works_today:
            continue
        serving = next((a for a in mine if a.status == Appointment.STATUS_IN_CONSULTATION), None)
        waiting = [a for a in mine if a.status == Appointment.STATUS_CHECKED_IN]
        rows.append({
            "doctor_id": d.id,
            "doctor_name": doctor_name(d),
            "department": d.department.name,
            "now_serving": serving.token_number if serving else None,
            "waiting": [a.token_number for a in waiting[:BOARD_WAITING_LIMIT]],
            "waiting_count": len(waiting),
        })
    rows.sort(key=lambda r: r["doctor_name"])
    return {
        "date": today.isoformat(),
        "updated_at": timezone.localtime().strftime("%H:%M:%S"),
        "doctors": rows,
    }


def broadcast_queue(hospital_id):
    """Push the fresh board to every connected WebSocket. Never raises."""
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if layer is None:
            return
        async_to_sync(layer.group_send)(
            f"queue_{hospital_id}",
            {"type": "queue.update", "board": board_snapshot(hospital_id)},
        )
    except Exception:
        pass  # realtime is a bonus: the screens still refresh by polling


def notify(hospital_id):
    """Broadcast once the database transaction (if any) has committed."""
    transaction.on_commit(lambda: broadcast_queue(hospital_id))