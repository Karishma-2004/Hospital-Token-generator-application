from django.conf import settings
from django.db import models
from doctors.models import Hospital, DoctorProfile


class Appointment(models.Model):
    STATUS_BOOKED = "BOOKED"
    STATUS_CHECKED_IN = "CHECKED_IN"
    STATUS_IN_CONSULTATION = "IN_CONSULTATION"
    STATUS_COMPLETED = "COMPLETED"
    STATUS_CANCELLED = "CANCELLED"

    STATUS = [
        (STATUS_BOOKED, "Booked"),
        (STATUS_CHECKED_IN, "Checked In"),
        (STATUS_IN_CONSULTATION, "In Consultation"),
        (STATUS_COMPLETED, "Completed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    # patient is empty for walk-in patients who have no Qenova account
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
        related_name="appointments", null=True, blank=True,
    )
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(DoctorProfile, on_delete=models.PROTECT, related_name="appointments")
    appointment_date = models.DateField()
    appointment_time = models.TimeField()
    end_time = models.TimeField()
    token_number = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS, default=STATUS_BOOKED)

    # ---- Sprint 5: check-in -------------------------------------------------
    is_walk_in = models.BooleanField(default=False)
    walk_in_name = models.CharField(max_length=120, blank=True)
    walk_in_phone = models.CharField(max_length=20, blank=True)
    # secret inside the patient's QR code; it can be used once (see ScanCheckInView)
    checkin_code = models.CharField(max_length=32, null=True, blank=True, unique=True, editable=False)
    checked_in_at = models.DateTimeField(null=True, blank=True)

    # ---- Sprint 6: queue ----------------------------------------------------
    called_at = models.DateTimeField(null=True, blank=True)      # doctor called the patient in
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "appointment_date", "appointment_time"],
                condition=models.Q(status__in=["BOOKED", "CHECKED_IN", "IN_CONSULTATION"], is_walk_in=False),
                name="unique_active_doctor_slot",
            ),
            models.UniqueConstraint(
                fields=["hospital", "appointment_date", "token_number"],
                name="unique_hospital_day_token",
            ),
        ]
        # Sprint 8: indexes for the queries the queue screens and reports run most often
        indexes = [
            models.Index(fields=["hospital", "appointment_date", "status"], name="appt_hosp_date_status_idx"),
            models.Index(fields=["doctor", "appointment_date", "status"], name="appt_doc_date_status_idx"),
            models.Index(fields=["patient", "appointment_date"], name="appt_patient_date_idx"),
        ]
        ordering = ["appointment_date", "appointment_time"]

    def __str__(self):
        return f"{self.hospital.name} - {self.appointment_date} #{self.token_number}"


# ======================================================================
# Sprint 7 - payments
# ======================================================================
class Payment(models.Model):
    """One consultation fee payment per appointment (online or cash at the desk)."""
    STATUS_PENDING = "PENDING"
    STATUS_PAID = "PAID"
    STATUS_FAILED = "FAILED"
    STATUS_REFUND_DUE = "REFUND_DUE"   # paid, then the appointment was cancelled: hospital refunds manually

    STATUS = [
        (STATUS_PENDING, "Pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_REFUND_DUE, "Refund due"),
    ]

    PROVIDER_MOCK = "mock"
    PROVIDER_RAZORPAY = "razorpay"
    PROVIDER_CASH = "cash"
    PROVIDERS = [
        (PROVIDER_MOCK, "Demo gateway"),
        (PROVIDER_RAZORPAY, "Razorpay"),
        (PROVIDER_CASH, "Cash at hospital"),
    ]

    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default="INR")
    status = models.CharField(max_length=12, choices=STATUS, default=STATUS_PENDING)
    provider = models.CharField(max_length=12, choices=PROVIDERS, default=PROVIDER_MOCK)
    provider_order_id = models.CharField(max_length=100, blank=True)
    provider_payment_id = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(null=True, blank=True)
    # how the fee is shared, fixed at the moment the payment succeeds (see payments.apply_split)
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)   # the platform's cut
    hospital_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)     # the hospital's share
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["status", "paid_at"], name="payment_status_paid_idx")]

    def __str__(self):
        return f"Payment {self.status} {self.amount} for appointment {self.appointment_id}"


# ======================================================================
# Sprint 7 - prescriptions
# ======================================================================
class Prescription(models.Model):
    appointment = models.OneToOneField(Appointment, on_delete=models.CASCADE, related_name="prescription")
    diagnosis = models.TextField()
    notes = models.TextField(blank=True)
    advice = models.TextField(blank=True)
    follow_up_date = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Prescription for appointment {self.appointment_id}"


class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="items")
    medicine = models.CharField(max_length=120)
    dosage = models.CharField(max_length=60, blank=True)         # e.g. 500 mg
    frequency = models.CharField(max_length=60, blank=True)      # e.g. 1-0-1
    duration = models.CharField(max_length=60, blank=True)       # e.g. 5 days
    instructions = models.CharField(max_length=200, blank=True)  # e.g. after food
    position = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["position", "id"]

    def __str__(self):
        return self.medicine


# ======================================================================
# Sprint 7 - notification log (also prevents sending the same reminder twice)
# ======================================================================
class NotificationLog(models.Model):
    CHANNEL_EMAIL = "EMAIL"
    CHANNEL_SMS = "SMS"
    CHANNELS = [(CHANNEL_EMAIL, "Email"), (CHANNEL_SMS, "SMS")]

    STATUS_SENT = "SENT"
    STATUS_FAILED = "FAILED"
    STATUS_SKIPPED = "SKIPPED"   # no email address / mobile number on file
    STATUSES = [(STATUS_SENT, "Sent"), (STATUS_FAILED, "Failed"), (STATUS_SKIPPED, "Skipped")]

    appointment = models.ForeignKey(Appointment, on_delete=models.CASCADE, related_name="notifications", null=True, blank=True)
    kind = models.CharField(max_length=40)
    channel = models.CharField(max_length=5, choices=CHANNELS)
    recipient = models.CharField(max_length=254, blank=True)
    status = models.CharField(max_length=8, choices=STATUSES)
    error = models.CharField(max_length=300, blank=True)
    # set only for messages that must go out once (reminders); unique so a second run cannot duplicate
    dedupe_key = models.CharField(max_length=120, null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.kind} {self.channel} {self.status}"
class Payout(models.Model):
    """The admin transferred `amount` to a hospital (bank / UPI) and records it here."""
    hospital = models.ForeignKey(Hospital, on_delete=models.PROTECT, related_name="payouts")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100)               # bank UTR / UPI reference number
    note = models.CharField(max_length=200, blank=True)
    paid_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="payouts_made"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]

    def __str__(self):
        return f"Payout {self.amount} to {self.hospital_id}"