import hmac
import re
from datetime import timedelta

from django.core.exceptions import ObjectDoesNotExist
from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from doctors.access import IsHospitalStaff
from doctors.models import DoctorProfile, Hospital
from . import payments, queue
from .models import Appointment

QR_PATTERN = re.compile(r"^MB1:(\d+):([A-Za-z0-9_\-]+)$")


class IsDoctor(permissions.BasePermission):
    """Doctor of an approved hospital. Puts the doctor profile on request.doctor."""
    message = "Doctor access required."

    def has_permission(self, request, view):
        user = request.user
        if not (user and user.is_authenticated and user.role == "DOCTOR"):
            return False
        try:
            profile = user.doctor_profile
        except ObjectDoesNotExist:
            return False
        if not (profile.is_active and profile.is_verified and profile.hospital.status == Hospital.STATUS_APPROVED):
            return False
        request.doctor = profile
        return True


# ======================================================================
# Sprint 5 - Receptionist
# ======================================================================
class ReceptionTodayView(APIView):
    """Landing data for the receptionist: today's list, doctors for walk-ins, counters."""
    permission_classes = [IsHospitalStaff]

    def get(self, request):
        hospital = request.hospital
        rows = (
            queue.todays(Appointment.objects.filter(hospital=hospital))
            .exclude(status=Appointment.STATUS_CANCELLED)
            .select_related("doctor__user", "patient", "payment", "prescription")
            .order_by("appointment_time", "token_number")
        )
        doctor_id = request.query_params.get("doctor")
        if doctor_id:
            rows = rows.filter(doctor_id=doctor_id)
        items = [queue.queue_item(a) for a in rows]
        counts = {
            "total": len(items),
            "booked": sum(1 for i in items if i["status"] == "BOOKED"),
            "waiting": sum(1 for i in items if i["status"] == "CHECKED_IN"),
            "in_consultation": sum(1 for i in items if i["status"] == "IN_CONSULTATION"),
            "completed": sum(1 for i in items if i["status"] == "COMPLETED"),
            "walk_ins": sum(1 for i in items if i["is_walk_in"]),
        }
        doctors = DoctorProfile.objects.select_related("user", "department").filter(
            hospital=hospital, is_active=True, is_verified=True
        ).order_by("user__first_name")
        return Response({
            "date": timezone.localdate().isoformat(),
            "hospital": {"id": hospital.id, "name": hospital.name},
            "doctors": [
                {"id": d.id, "name": queue.doctor_name(d), "department": d.department.name}
                for d in doctors
            ],
            "counts": counts,
            "appointments": items,
        })


class ScanCheckInView(APIView):
    """Check a patient in from the QR code on their ticket. Each QR works exactly once."""
    permission_classes = [IsHospitalStaff]

    def post(self, request):
        text = str(request.data.get("payload", "")).strip()
        match = QR_PATTERN.match(text)
        if not match:
            return Response({"detail": "This is not a Qenova QR code."}, status=400)
        appointment_id, code = int(match.group(1)), match.group(2)

        with transaction.atomic():
            appointment = (
                Appointment.objects.select_for_update()
                .select_related("doctor__user", "patient")
                .filter(id=appointment_id, hospital=request.hospital)
                .first()
            )
            # same message for "no such ticket" and "wrong code" so codes cannot be guessed
            if not appointment or not appointment.checkin_code or not hmac.compare_digest(appointment.checkin_code, code):
                return Response({"detail": "Invalid QR code for this hospital."}, status=404)

            if appointment.status == Appointment.STATUS_CANCELLED:
                return Response({"detail": "This appointment was cancelled."}, status=400)
            if appointment.status != Appointment.STATUS_BOOKED:
                when = ""
                if appointment.checked_in_at:
                    when = " at " + timezone.localtime(appointment.checked_in_at).strftime("%H:%M")
                return Response({"detail": f"This QR code was already used{when}."}, status=409)
            if appointment.appointment_date != timezone.localdate():
                return Response(
                    {"detail": f"This appointment is for {appointment.appointment_date}, not today."},
                    status=400,
                )
            if payments.payment_state(appointment) == "UNPAID":
                return Response(
                    {"detail": "The consultation fee is not paid yet. Record the cash payment first, or ask the patient to pay online."},
                    status=400,
                )

            queue.check_in(appointment)
            queue.notify(appointment.hospital_id)

        return Response({
            "message": "Checked in.",
            "appointment": queue.queue_item(appointment),
        })


class WalkInView(APIView):
    """Register a patient who arrived without a booking and give them a token."""
    permission_classes = [IsHospitalStaff]

    def post(self, request):
        name = str(request.data.get("name", "")).strip()
        phone = str(request.data.get("phone", "")).strip()
        if not name:
            return Response({"name": ["Patient name is required."]}, status=400)
        if len(name) > 120:
            return Response({"name": ["Name is too long."]}, status=400)
        if phone and not re.fullmatch(r"[0-9+\-\s]{6,20}", phone):
            return Response({"phone": ["Enter a valid phone number."]}, status=400)

        try:
            doctor = DoctorProfile.objects.select_related("user", "hospital").get(
                id=request.data.get("doctor"), hospital=request.hospital,
                is_active=True, is_verified=True,
            )
        except (DoctorProfile.DoesNotExist, TypeError, ValueError):
            return Response({"doctor": ["Select a doctor of your hospital."]}, status=400)

        now = timezone.localtime().replace(second=0, microsecond=0)
        today = now.date()
        for _ in range(3):  # retry if two walk-ins get the same token at the same moment
            try:
                with transaction.atomic():
                    max_token = Appointment.objects.filter(
                        hospital=request.hospital, appointment_date=today
                    ).aggregate(m=Max("token_number"))["m"] or 0
                    appointment = Appointment.objects.create(
                        patient=None, is_walk_in=True, walk_in_name=name, walk_in_phone=phone,
                        hospital=request.hospital, doctor=doctor,
                        appointment_date=today, appointment_time=now.time(),
                        end_time=(now + timedelta(minutes=15)).time(),
                        token_number=max_token + 1,
                        status=Appointment.STATUS_CHECKED_IN, checked_in_at=timezone.now(),
                    )
                    queue.notify(request.hospital.id)
                break
            except IntegrityError:
                continue
        else:
            return Response({"detail": "Could not generate a token. Please try again."}, status=409)

        return Response({
            "message": "Walk-in registered and added to the queue.",
            "appointment": queue.queue_item(appointment),
            "patients_ahead": queue.patient_queue_info(appointment)["patients_ahead"],
        }, status=201)


# ======================================================================
# Sprint 6 - Doctor
# ======================================================================
class DoctorQueueView(APIView):
    """Today's queue for the logged-in doctor."""
    permission_classes = [IsDoctor]

    def get(self, request):
        doctor = request.doctor
        rows = list(
            queue.todays(Appointment.objects.filter(doctor=doctor))
            .exclude(status=Appointment.STATUS_CANCELLED)
            .select_related("doctor__user", "patient", "payment", "prescription")
            .order_by("checked_in_at", "appointment_time", "id")
        )
        current = next((a for a in rows if a.status == Appointment.STATUS_IN_CONSULTATION), None)
        waiting = [a for a in rows if a.status == Appointment.STATUS_CHECKED_IN]
        upcoming = sorted(
            (a for a in rows if a.status == Appointment.STATUS_BOOKED),
            key=lambda a: (a.appointment_time, a.id),
        )
        avg = queue.average_consult_minutes(doctor)

        waiting_items = []
        for index, a in enumerate(waiting):
            item = queue.queue_item(a)
            item["position"] = index + 1
            item["estimated_wait_minutes"] = int(round(index * avg + (avg if current else 0)))
            waiting_items.append(item)

        return Response({
            "date": timezone.localdate().isoformat(),
            "hospital_id": doctor.hospital_id,
            "doctor_name": queue.doctor_name(doctor),
            "average_minutes": avg,
            "current": queue.queue_item(current) if current else None,
            "waiting": waiting_items,
            "upcoming": [queue.queue_item(a) for a in upcoming],
            "completed_count": sum(1 for a in rows if a.status == Appointment.STATUS_COMPLETED),
            "recent_completed": [
                queue.queue_item(a) for a in sorted(
                    (a for a in rows if a.status == Appointment.STATUS_COMPLETED),
                    key=lambda a: a.completed_at or a.updated_at, reverse=True,
                )[:10]
            ],
        })


class DoctorCallNextView(APIView):
    """Finishes the current patient (if any) and calls the next one in the queue."""
    permission_classes = [IsDoctor]

    def post(self, request):
        nxt = queue.call_next(request.doctor)
        queue.notify(request.doctor.hospital_id)
        if not nxt:
            return Response({"message": "No patients are waiting.", "called": None})
        return Response({"message": f"Token #{nxt.token_number} called in.", "called": queue.queue_item(nxt)})


class DoctorCompleteView(APIView):
    """Finish the current consultation without calling anyone new (e.g. end of the day)."""
    permission_classes = [IsDoctor]

    def post(self, request):
        with transaction.atomic():
            current = Appointment.objects.select_for_update().filter(
                doctor=request.doctor, appointment_date=timezone.localdate(),
                status=Appointment.STATUS_IN_CONSULTATION,
            )
            done = 0
            for a in list(current):
                queue.complete(a)
                done += 1
            queue.notify(request.doctor.hospital_id)
        return Response({"message": "Consultation completed." if done else "No active consultation."})


# ======================================================================
# Live queue: public board + patient status
# ======================================================================
class QueueBoardView(APIView):
    """Public data for the lobby display. Token numbers only - no patient names."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def get(self, request, hospital_id):
        hospital = Hospital.objects.filter(id=hospital_id, status=Hospital.STATUS_APPROVED).first()
        if not hospital:
            return Response({"detail": "Hospital not found."}, status=404)
        board = queue.board_snapshot(hospital.id)
        board["hospital"] = {"id": hospital.id, "name": hospital.name}
        return Response(board)


class MyQueueView(APIView):
    """The logged-in patient's appointments for today with position and wait estimate."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        if request.user.role != "USER":
            return Response({"items": []})
        rows = (
            queue.todays(Appointment.objects.filter(patient=request.user))
            .filter(status__in=[
                Appointment.STATUS_BOOKED, Appointment.STATUS_CHECKED_IN, Appointment.STATUS_IN_CONSULTATION,
            ])
            .select_related("doctor__user", "hospital")
            .prefetch_related("doctor__schedules")
            .order_by("appointment_time")
        )
        return Response({"items": [queue.patient_queue_info(a) for a in rows]})