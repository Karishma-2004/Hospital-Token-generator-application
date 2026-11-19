from django.conf import settings
from django.db import models


class Hospital(models.Model):
    STATUS_PENDING = "PENDING"
    STATUS_APPROVED = "APPROVED"
    STATUS_REJECTED = "REJECTED"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    name = models.CharField(max_length=200)
    registration_number = models.CharField(
        max_length=100,
        unique=True,
    )
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    pincode = models.CharField(max_length=10)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    description = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )

    # Receptionist / hospital registration account
    admin_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_hospital",
    )

    rejection_reason = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class HospitalStaff(models.Model):
    """
    Links a receptionist login to exactly one hospital.

    The application has only these hospital-side roles:
        - Hospital registration/receptionist account
        - Receptionist

    Both use User.role == RECEPTIONIST.
    """

    ROLE_ADMIN = "HOSPITAL_ADMIN"
    ROLE_RECEPTIONIST = "RECEPTIONIST"

    ROLE_CHOICES = [
        (ROLE_ADMIN, "Hospital admin"),
        (ROLE_RECEPTIONIST, "Receptionist"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hospital_staff",
    )

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="staff",
    )

    staff_role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default=ROLE_RECEPTIONIST,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} @ {self.hospital} ({self.staff_role})"


class Department(models.Model):
    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="departments",
    )

    name = models.CharField(max_length=100)

    description = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["hospital", "name"],
                name="unique_hospital_department",
            )
        ]
        ordering = ["name"]

    def __str__(self):
        return f"{self.hospital.name} - {self.name}"


class DoctorProfile(models.Model):
    """
    Professional profile for a doctor.

    Login information such as:
        - email
        - username
        - password
        - mobile

    belongs to the related User model.

    DoctorProfile contains only professional/hospital information.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="doctor_profile",
    )

    hospital = models.ForeignKey(
        Hospital,
        on_delete=models.CASCADE,
        related_name="doctors",
    )

    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        related_name="doctors",
    )

    specialization = models.CharField(
        max_length=120,
    )

    consultation_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    experience_years = models.PositiveIntegerField(
        default=0,
    )

    bio = models.TextField(
        blank=True,
    )

    registration_number = models.CharField(
        max_length=100,
        unique=True,
    )

    is_verified = models.BooleanField(
        default=False,
    )

    is_active = models.BooleanField(
        default=True,
    )

    def __str__(self):
        return f"Dr. {self.user.get_full_name() or self.user.username}"


class DoctorSchedule(models.Model):
    WEEKDAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    doctor = models.ForeignKey(
        DoctorProfile,
        on_delete=models.CASCADE,
        related_name="schedules",
    )

    weekday = models.PositiveSmallIntegerField(
        choices=WEEKDAYS,
    )

    start_time = models.TimeField()

    end_time = models.TimeField()

    slot_minutes = models.PositiveIntegerField(
        default=15,
    )

    is_active = models.BooleanField(
        default=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "doctor",
                    "weekday",
                    "start_time",
                    "end_time",
                ],
                name="doctors_doctor_schedule_unique",
            )
        ]

        ordering = [
            "weekday",
            "start_time",
        ]

    def __str__(self):
        return (
            f"{self.doctor} - "
            f"{self.get_weekday_display()} "
            f"{self.start_time}-{self.end_time}"
        )