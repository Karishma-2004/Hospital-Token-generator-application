import secrets
from datetime import date, datetime, timedelta

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from doctors.access import get_staff_hospital, is_application_admin
from doctors.models import DoctorProfile, Hospital
from . import notify, payments, queue
from .models import Appointment
from .scheduling import active_schedules, is_past, slot_end
from .serializers import AppointmentSerializer, BookAppointmentSerializer

ACTIVE = [
    Appointment.STATUS_BOOKED,
    Appointment.STATUS_CHECKED_IN,
    Appointment.STATUS_IN_CONSULTATION,
]


class AppointmentViewSet(viewsets.ModelViewSet):
    """All endpoints need a valid JWT (DRF default). Data is scoped per role."""
    serializer_class = AppointmentSerializer
    http_method_names = ["get", "post", "put", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related(
            "doctor__user", "doctor__department", "doctor__hospital", "hospital", "patient",
            "payment", "prescription",
        ).prefetch_related("doctor__schedules")
        if is_application_admin(user):
            return qs
        if user.role == "RECEPTIONIST":
            hospital = get_staff_hospital(user)
            return qs.filter(hospital=hospital) if hospital else qs.none()
        if user.role == "DOCTOR":
            try:
                return qs.filter(doctor=user.doctor_profile)
            except DoctorProfile.DoesNotExist:
                return qs.none()
        return qs.filter(patient=user)

    # ---- book -----------------------------------------------------------
    def create(self, request, *args, **kwargs):
        if request.user.role != "USER":
            return Response({"detail": "Only patients can book appointments."}, status=403)
        serializer = BookAppointmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doctor = serializer.validated_data["doctor"]
        day = serializer.validated_data["appointment_date"]
        tm = serializer.validated_data["appointment_time"]
        schedule = serializer.validated_data["schedule"]

        try:
            with transaction.atomic():
                if Appointment.objects.select_for_update().filter(
                    doctor=doctor, appointment_date=day, appointment_time=tm,
                    status__in=ACTIVE, is_walk_in=False,
                ).exists():
                    return Response({"detail": "This slot is already booked."}, status=409)
                max_token = Appointment.objects.filter(
                    hospital=doctor.hospital, appointment_date=day
                ).aggregate(m=Max("token_number"))["m"] or 0
                appointment = Appointment.objects.create(
                    patient=request.user, hospital=doctor.hospital, doctor=doctor,
                    appointment_date=day, appointment_time=tm,
                    end_time=slot_end(day, tm, schedule), token_number=max_token + 1,
                    checkin_code=secrets.token_urlsafe(12),
                )
                queue.notify(doctor.hospital_id)
                notify.booking_confirmed(appointment)
        except IntegrityError:
            return Response({"detail": "That slot was just taken by someone else. Please pick another slot."}, status=409)
        return Response(AppointmentSerializer(appointment, context={"request": request}).data, status=201)

    # ---- reschedule (patient only) -------------------------------------
    def update(self, request, *args, **kwargs):
        appointment = self.get_object()
        if appointment.patient_id != request.user.id:
            return Response({"detail": "You can only reschedule your own appointment."}, status=403)
        if appointment.status != Appointment.STATUS_BOOKED:
            return Response({"detail": "Only booked appointments can be rescheduled."}, status=400)
        serializer = BookAppointmentSerializer(data={
            "doctor": appointment.doctor_id,
            "appointment_date": request.data.get("appointment_date"),
            "appointment_time": request.data.get("appointment_time"),
        })
        serializer.is_valid(raise_exception=True)
        day = serializer.validated_data["appointment_date"]
        tm = serializer.validated_data["appointment_time"]
        schedule = serializer.validated_data["schedule"]
        try:
            with transaction.atomic():
                if Appointment.objects.filter(
                    doctor=appointment.doctor, appointment_date=day, appointment_time=tm,
                    status__in=ACTIVE, is_walk_in=False,
                ).exclude(pk=appointment.pk).exists():
                    return Response({"detail": "That slot is already booked."}, status=409)
                if day != appointment.appointment_date:
                    # token numbers are per hospital per day, so a new day needs a new token
                    max_token = Appointment.objects.filter(
                        hospital=appointment.hospital, appointment_date=day
                    ).aggregate(m=Max("token_number"))["m"] or 0
                    appointment.token_number = max_token + 1
                appointment.appointment_date = day
                appointment.appointment_time = tm
                appointment.end_time = slot_end(day, tm, schedule)
                appointment.save(update_fields=["appointment_date", "appointment_time", "end_time", "token_number", "updated_at"])
                queue.notify(appointment.hospital_id)
                notify.booking_rescheduled(appointment)
        except IntegrityError:
            return Response({"detail": "That slot was just taken by someone else. Please pick another slot."}, status=409)
        return Response(self.get_serializer(appointment).data)

    partial_update = update

    # ---- cancel ---------------------------------------------------------
    def destroy(self, request, *args, **kwargs):
        appointment = self.get_object()  # queryset is already role-scoped
        if appointment.status in (Appointment.STATUS_COMPLETED, Appointment.STATUS_CANCELLED):
            return Response({"detail": f"A {appointment.status.lower()} appointment cannot be cancelled."}, status=400)
        if appointment.status == Appointment.STATUS_IN_CONSULTATION:
            return Response({"detail": "This patient is already with the doctor."}, status=400)
        if request.user.role == "DOCTOR":
            return Response({"detail": "Doctors cannot cancel appointments."}, status=403)
        with transaction.atomic():
            appointment.status = Appointment.STATUS_CANCELLED
            appointment.save(update_fields=["status", "updated_at"])
            refund_due = payments.mark_refund_due(appointment)
            queue.notify(appointment.hospital_id)
            notify.booking_cancelled(appointment, refund_due)
        return Response(status=204)

    # ---- manual status change ------------------------------------------
    @action(detail=True, methods=["post"], url_path="status")
    def set_status(self, request, pk=None):
        """Receptionist: BOOKED -> CHECKED_IN (manual check-in, for patients without the QR).
        Doctor or receptionist: CHECKED_IN / IN_CONSULTATION -> COMPLETED."""
        appointment = self.get_object()
        new = request.data.get("status")
        role = request.user.role
        allowed = {
            Appointment.STATUS_CHECKED_IN: ("RECEPTIONIST",),
            Appointment.STATUS_COMPLETED: ("DOCTOR", "RECEPTIONIST"),
        }
        if new not in allowed:
            return Response({"detail": "Status must be CHECKED_IN or COMPLETED."}, status=400)
        if role not in allowed[new]:
            return Response({"detail": "You are not allowed to set this status."}, status=403)

        with transaction.atomic():
            if new == Appointment.STATUS_CHECKED_IN:
                if appointment.status != Appointment.STATUS_BOOKED:
                    return Response({"detail": "Appointment must be BOOKED first."}, status=400)
                if appointment.appointment_date != timezone.localdate():
                    return Response({"detail": "Only today's appointments can be checked in."}, status=400)
                queue.check_in(appointment)
            else:
                if appointment.status not in (Appointment.STATUS_CHECKED_IN, Appointment.STATUS_IN_CONSULTATION):
                    return Response({"detail": "Patient must be checked in first."}, status=400)
                queue.complete(appointment)
            queue.notify(appointment.hospital_id)
        return Response(self.get_serializer(appointment).data)


class DoctorSlotsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, doctor_id):
        date_value = request.query_params.get("date")
        if not date_value:
            return Response({"detail": "date is required in YYYY-MM-DD format."}, status=400)
        try:
            day = date.fromisoformat(date_value)
        except ValueError:
            return Response({"detail": "Invalid date."}, status=400)
        try:
            doctor = DoctorProfile.objects.select_related("hospital", "department", "user").prefetch_related("schedules").get(
                id=doctor_id, is_active=True, is_verified=True, hospital__status=Hospital.STATUS_APPROVED
            )
        except DoctorProfile.DoesNotExist:
            return Response({"detail": "Doctor not found."}, status=404)

        booked = {
            a.appointment_time: a
            for a in Appointment.objects.filter(
                doctor=doctor, appointment_date=day, status__in=ACTIVE, is_walk_in=False
            )
        }
        slots = []
        for schedule in sorted(active_schedules(doctor, day), key=lambda s: s.start_time):
            start = datetime.combine(day, schedule.start_time)
            end = datetime.combine(day, schedule.end_time)
            step = timedelta(minutes=schedule.slot_minutes)
            while start + step <= end:
                appt = booked.get(start.time())
                if appt:
                    state = "BOOKED"
                elif is_past(day, start.time()):
                    state = "PAST"
                else:
                    state = "AVAILABLE"
                slots.append({
                    "start_time": start.strftime("%H:%M"),
                    "end_time": (start + step).strftime("%H:%M"),
                    "status": state,
                })
                start += step
        return Response({
            "doctor": doctor.user.get_full_name() or doctor.user.username,
            "specialization": doctor.specialization,
            "hospital": doctor.hospital.name,
            "date": date_value,
            "slots": slots,
        })