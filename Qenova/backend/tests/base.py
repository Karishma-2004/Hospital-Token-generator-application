"""Shared helpers for the automated tests. Run everything with:  python manage.py test"""
import secrets
from datetime import datetime, time, timedelta

from django.core.cache import cache
from django.db.models import Max
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from appointments.models import Appointment
from doctors.models import Department, DoctorProfile, DoctorSchedule, Hospital, HospitalStaff

# fast password hashing, no background threads, demo payment gateway, console SMS
test_settings = override_settings(
    PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"],
    NOTIFY_ASYNC=False,
    PAYMENT_PROVIDER="mock",
    SMS_PROVIDER="console",
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)

PASSWORD = "Passw0rd!Test"


def rows(response):
    data = response.data
    return data["results"] if isinstance(data, dict) and "results" in data else data


def make_user(username, role=User.ROLE_USER, **extra):
    return User.objects.create_user(
        username=username, email=f"{username}@example.test", password=PASSWORD, role=role,
        is_active=True, email_verified=True, first_name=username.title(), last_name="Test", **extra,
    )


_counter = {"n": 0}


def _next():
    _counter["n"] += 1
    return _counter["n"]


def make_hospital(name="City Hospital", approved=True):
    n = _next()
    admin_user = make_user(f"hadmin{n}", User.ROLE_RECEPTIONIST)
    hospital = Hospital.objects.create(
        name=name, registration_number=f"REG-{n}", address="1 Main Road", city="Hyderabad",
        state="Telangana", pincode="500001", phone="9000000000", email=f"h{n}@example.test",
        status=Hospital.STATUS_APPROVED if approved else Hospital.STATUS_PENDING, admin_user=admin_user,
    )
    HospitalStaff.objects.create(user=admin_user, hospital=hospital, staff_role=HospitalStaff.ROLE_ADMIN)
    return hospital, admin_user


def make_receptionist(hospital):
    user = make_user(f"recep{_next()}", User.ROLE_RECEPTIONIST)
    HospitalStaff.objects.create(user=user, hospital=hospital, staff_role=HospitalStaff.ROLE_RECEPTIONIST)
    return user


def make_doctor(hospital, fee=500, department="General Medicine"):
    n = _next()
    user = make_user(f"doc{n}", User.ROLE_DOCTOR)
    dept, _ = Department.objects.get_or_create(hospital=hospital, name=department)
    return DoctorProfile.objects.create(
        user=user, hospital=hospital, department=dept, specialization="Physician",
        consultation_fee=fee, registration_number=f"MC-{n}", is_verified=True, is_active=True,
    )


def make_schedule(doctor, weekday, start="09:00", end="10:00", minutes=15):
    return DoctorSchedule.objects.create(
        doctor=doctor, weekday=weekday, start_time=time.fromisoformat(start),
        end_time=time.fromisoformat(end), slot_minutes=minutes,
    )


def make_appointment(patient, doctor, day=None, at="10:00", status=Appointment.STATUS_BOOKED, **extra):
    day = day or timezone.localdate()
    start = time.fromisoformat(at)
    token = (Appointment.objects.filter(hospital=doctor.hospital, appointment_date=day)
             .aggregate(m=Max("token_number"))["m"] or 0) + 1
    defaults = dict(
        patient=patient, hospital=doctor.hospital, doctor=doctor, appointment_date=day,
        appointment_time=start, end_time=(datetime.combine(day, start) + timedelta(minutes=15)).time(),
        token_number=token, status=status, checkin_code=secrets.token_urlsafe(10),
    )
    defaults.update(extra)
    return Appointment.objects.create(**defaults)


def tomorrow():
    return timezone.localdate() + timedelta(days=1)


class BaseCase(TestCase):
    def setUp(self):
        cache.clear()  # resets the login throttle between tests
        self.client = APIClient()

    def login_as(self, user):
        token = RefreshToken.for_user(user).access_token
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")

    def logout(self):
        self.client.credentials()
