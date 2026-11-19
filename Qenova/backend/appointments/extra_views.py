"""Sprint 7 endpoints: payments and prescriptions."""
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from doctors.access import IsHospitalStaff
from . import notify, payments, queue
from .models import Appointment, Payment
from .serializers import PrescriptionSerializer

BASE = Appointment.objects.select_related(
    "doctor__user", "doctor__department", "doctor__hospital", "hospital", "patient", "payment", "prescription"
)


# ======================================================================
# Payments
# ======================================================================
class PaymentConfigView(APIView):
    """Tells the browser which gateway is active."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        active = payments.provider()
        return Response({
            "provider": active,
            "currency": "INR",
            "key_id": getattr(settings, "RAZORPAY_KEY_ID", "") if active == "razorpay" else "",
        })


class PayOrderView(APIView):
    """Patient starts paying the consultation fee of their own appointment."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        appointment = BASE.filter(pk=pk, patient=request.user).first()
        if not appointment:
            return Response({"detail": "Appointment not found."}, status=404)
        if appointment.status == Appointment.STATUS_CANCELLED:
            return Response({"detail": "This appointment was cancelled."}, status=400)
        try:
            with transaction.atomic():
                order = payments.create_order(appointment)
        except payments.PaymentError as exc:
            return Response({"detail": exc.message}, status=exc.status)
        return Response(order)


class PayVerifyView(APIView):
    """Browser reports the gateway result; the server checks the signature before marking PAID."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        appointment = BASE.filter(pk=pk, patient=request.user).first()
        if not appointment:
            return Response({"detail": "Appointment not found."}, status=404)
        already_paid = getattr(appointment, "payment", None) is not None and appointment.payment.status == Payment.STATUS_PAID
        try:
            with transaction.atomic():
                payment = payments.verify_payment(
                    appointment,
                    str(request.data.get("order_id", "")),
                    str(request.data.get("payment_id", "")),
                    str(request.data.get("signature", "")),
                )
                if not already_paid:
                    notify.payment_received(appointment, payment)
        except payments.PaymentError as exc:
            return Response({"detail": exc.message}, status=exc.status)
        return Response({"message": "Payment successful.", "payment_status": payments.payment_state(appointment)})


class PayCashView(APIView):
    """Receptionist records a cash payment taken at the desk."""
    permission_classes = [IsHospitalStaff]

    def post(self, request, pk):
        appointment = BASE.filter(pk=pk, hospital=request.hospital).first()
        if not appointment:
            return Response({"detail": "Appointment not found."}, status=404)
        if appointment.status == Appointment.STATUS_CANCELLED:
            return Response({"detail": "This appointment was cancelled."}, status=400)
        try:
            with transaction.atomic():
                payment = payments.record_cash(appointment)
                notify.payment_received(appointment, payment)
        except payments.PaymentError as exc:
            return Response({"detail": exc.message}, status=exc.status)
        return Response({"message": "Cash payment recorded.", "payment_status": "PAID"})


# ======================================================================
# Prescriptions
# ======================================================================
def prescription_payload(appointment, prescription):
    doctor = appointment.doctor
    hospital = appointment.hospital
    return {
        "prescription": PrescriptionSerializer(prescription).data,
        "appointment": {
            "id": appointment.id,
            "token_number": appointment.token_number,
            "appointment_date": appointment.appointment_date.isoformat(),
            "appointment_time": appointment.appointment_time.strftime("%H:%M"),
            "patient_name": queue.display_name(appointment),
            "status": appointment.status,
        },
        "doctor": {
            "name": queue.doctor_name(doctor),
            "specialization": doctor.specialization,
            "registration_number": doctor.registration_number,
            "department": doctor.department.name,
        },
        "hospital": {
            "name": hospital.name,
            "address": hospital.address,
            "city": hospital.city,
            "phone": hospital.phone,
        },
    }


def _doctor_profile(user):
    if user.role != "DOCTOR":
        return None
    try:
        return user.doctor_profile
    except ObjectDoesNotExist:
        return None


class PrescriptionView(APIView):
    """GET: the patient or the doctor of that appointment. PUT: the doctor only."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        appointment = BASE.filter(pk=pk).first()
        profile = _doctor_profile(request.user)
        allowed = appointment and (
            (appointment.patient_id and appointment.patient_id == request.user.id)
            or (profile and appointment.doctor_id == profile.id)
        )
        if not allowed:
            return Response({"detail": "Prescription not found."}, status=404)
        prescription = getattr(appointment, "prescription", None)
        if prescription is None:
            return Response({"detail": "No prescription has been written for this appointment."}, status=404)
        return Response(prescription_payload(appointment, prescription))

    def put(self, request, pk):
        profile = _doctor_profile(request.user)
        if profile is None:
            return Response({"detail": "Only the treating doctor can write a prescription."}, status=403)
        appointment = BASE.filter(pk=pk, doctor=profile).first()
        if not appointment:
            return Response({"detail": "Appointment not found."}, status=404)
        if appointment.status not in (Appointment.STATUS_IN_CONSULTATION, Appointment.STATUS_COMPLETED):
            return Response({"detail": "A prescription can be written once the patient has been called in."}, status=400)

        existing = getattr(appointment, "prescription", None)
        serializer = PrescriptionSerializer(existing, data=request.data, context={"appointment": appointment})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            prescription = serializer.save()
            if existing is None:
                notify.prescription_ready(appointment)
        return Response(prescription_payload(appointment, prescription), status=200 if existing else 201)
