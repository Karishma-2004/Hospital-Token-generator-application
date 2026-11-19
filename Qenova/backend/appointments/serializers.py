import secrets

from django.utils import timezone
from rest_framework import serializers

from doctors.models import DoctorProfile
from doctors.serializers import DoctorSerializer
from .models import Appointment, Prescription, PrescriptionItem
from .payments import fee_for, payment_state
from .queue import display_name
from .scheduling import MAX_DAYS_AHEAD, find_schedule, is_past


class AppointmentSerializer(serializers.ModelSerializer):
    doctor_detail = DoctorSerializer(source="doctor", read_only=True)
    hospital_name = serializers.CharField(source="hospital.name", read_only=True)
    patient_name = serializers.SerializerMethodField()
    qr_payload = serializers.SerializerMethodField()
    fee = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    has_prescription = serializers.SerializerMethodField()

    class Meta:
        model = Appointment
        fields = [
            "id", "patient", "patient_name", "hospital", "hospital_name", "doctor", "doctor_detail",
            "appointment_date", "appointment_time", "end_time", "token_number",
            "status", "is_walk_in", "checked_in_at", "qr_payload",
            "fee", "payment_status", "has_prescription", "created_at", "updated_at",
        ]
        read_only_fields = [
            "patient", "hospital", "token_number", "status", "is_walk_in", "checked_in_at",
            "created_at", "updated_at", "end_time",
        ]

    def get_patient_name(self, obj):
        return display_name(obj)

    def get_fee(self, obj):
        return str(fee_for(obj))

    def get_payment_status(self, obj):
        return payment_state(obj)

    def get_has_prescription(self, obj):
        return getattr(obj, "prescription", None) is not None

    def get_qr_payload(self, obj):
        """The one-time check-in QR text. Only the patient who owns the booking ever receives it,
        only while the ticket is unused (status BOOKED), and only once the fee is paid."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        if obj.patient_id != request.user.id or obj.status != Appointment.STATUS_BOOKED:
            return None
        if payment_state(obj) == "UNPAID":
            return None   # the QR ticket is created once the consultation fee is paid
        if not obj.checkin_code:
            # bookings made before the QR feature existed get their code the first time the patient opens them
            obj.checkin_code = secrets.token_urlsafe(12)
            obj.save(update_fields=["checkin_code"])
        return f"MB1:{obj.id}:{obj.checkin_code}"


class BookAppointmentSerializer(serializers.Serializer):
    doctor = serializers.PrimaryKeyRelatedField(queryset=DoctorProfile.objects.all())
    appointment_date = serializers.DateField()
    appointment_time = serializers.TimeField()

    def validate(self, data):
        doctor = data["doctor"]
        day = data["appointment_date"]
        tm = data["appointment_time"]
        if not doctor.is_active or not doctor.is_verified or doctor.hospital.status != "APPROVED":
            raise serializers.ValidationError("This doctor is not available for booking.")
        if doctor.department.hospital_id != doctor.hospital_id:
            raise serializers.ValidationError("Doctor hospital and department do not match.")
        if is_past(day, tm):
            raise serializers.ValidationError("You cannot book a time that has already passed.")
        if (day - timezone.localdate()).days > MAX_DAYS_AHEAD:
            raise serializers.ValidationError(f"Appointments can be booked up to {MAX_DAYS_AHEAD} days ahead.")
        schedule = find_schedule(doctor, day, tm)
        if not schedule:
            raise serializers.ValidationError("Select one of the displayed appointment slots for this doctor.")
        data["schedule"] = schedule
        return data


# ======================================================================
# Sprint 7 - prescriptions
# ======================================================================
class PrescriptionItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = PrescriptionItem
        fields = ["medicine", "dosage", "frequency", "duration", "instructions"]


class PrescriptionSerializer(serializers.ModelSerializer):
    items = PrescriptionItemSerializer(many=True, required=False)

    class Meta:
        model = Prescription
        fields = ["id", "diagnosis", "notes", "advice", "follow_up_date", "items", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_items(self, items):
        if len(items) > 20:
            raise serializers.ValidationError("A prescription can list at most 20 medicines.")
        return items

    def validate_follow_up_date(self, value):
        if value and value < timezone.localdate():
            raise serializers.ValidationError("Follow-up date cannot be in the past.")
        return value

    @staticmethod
    def _write_items(prescription, items):
        prescription.items.all().delete()
        PrescriptionItem.objects.bulk_create([
            PrescriptionItem(prescription=prescription, position=index, **item)
            for index, item in enumerate(items)
        ])

    def create(self, validated_data):
        items = validated_data.pop("items", [])
        prescription = Prescription.objects.create(appointment=self.context["appointment"], **validated_data)
        self._write_items(prescription, items)
        return prescription

    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        instance.save()
        if items is not None:
            self._write_items(instance, items)
        return instance