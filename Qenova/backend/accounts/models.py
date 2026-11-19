from django.contrib.auth.models import AbstractUser, UserManager as DjangoUserManager
from django.db import models


class MediBookUserManager(DjangoUserManager):
    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", "ADMIN")
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("email_verified", True)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    ROLE_USER = "USER"
    ROLE_DOCTOR = "DOCTOR"
    ROLE_RECEPTIONIST = "RECEPTIONIST"
    ROLE_ADMIN = "ADMIN"

    ROLE_CHOICES = [
        (ROLE_USER, "User"),
        (ROLE_DOCTOR, "Doctor"),
        (ROLE_RECEPTIONIST, "Receptionist"),
        (ROLE_ADMIN, "Application Admin"),
    ]

    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    mobile = models.CharField(max_length=20, blank=True)
    email_verified = models.BooleanField(default=False)

    objects = MediBookUserManager()

    def __str__(self):
        return self.username


class EmailVerificationCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="verification_codes")
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Verification code for {self.user.email}"
