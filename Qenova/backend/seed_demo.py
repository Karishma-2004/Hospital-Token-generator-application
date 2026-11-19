import os
from datetime import time

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django

django.setup()

from accounts.models import User
from doctors.models import Hospital, HospitalStaff, Department, DoctorProfile, DoctorSchedule


def user(username, email, password, role, first, last, active=True):
    obj, _ = User.objects.get_or_create(username=username, defaults={
        "email": email, "role": role, "first_name": first, "last_name": last,
        "is_active": active, "email_verified": True,
    })
    obj.email = email
    obj.role = role
    obj.first_name = first
    obj.last_name = last
    obj.is_active = active
    obj.email_verified = True
    obj.set_password(password)
    obj.save()
    return obj


admin = user("admin", "admin@medibook.local", "Admin@123", User.ROLE_ADMIN, "Application", "Admin")
admin.is_staff = True
admin.is_superuser = True
admin.save(update_fields=["is_staff", "is_superuser"])

patient = user("user", "user@medibook.local", "User@123", User.ROLE_USER, "Demo", "User")

hospital_admin = user("receptionist", "receptionist@medibook.local", "Receptionist@123", User.ROLE_RECEPTIONIST, "Demo", "Receptionist")
hospital, _ = Hospital.objects.get_or_create(
    registration_number="DEMO-MEDIBOOK-001",
    defaults={
        "name": "Qenova Demo Hospital",
        "address": "Hitech City",
        "city": "Hyderabad",
        "state": "Telangana",
        "pincode": "500081",
        "phone": "9000000000",
        "email": "demo-hospital@medibook.local",
        "description": "Demo hospital for Qenova development.",
        "status": Hospital.STATUS_APPROVED,
        "admin_user": hospital_admin,
    },
)
hospital.status = Hospital.STATUS_APPROVED
hospital.admin_user = hospital_admin
hospital.save()
HospitalStaff.objects.update_or_create(
    user=hospital_admin, defaults={"hospital": hospital, "staff_role": HospitalStaff.ROLE_ADMIN},
)

cardiology, _ = Department.objects.get_or_create(hospital=hospital, name="Cardiology", defaults={"description": "Heart and cardiovascular care"})
neurology, _ = Department.objects.get_or_create(hospital=hospital, name="Neurology", defaults={"description": "Brain and nervous system care"})

doctor_user = user("doctor", "doctor@medibook.local", "Doctor@123", User.ROLE_DOCTOR, "Asha", "Reddy")
doctor, _ = DoctorProfile.objects.get_or_create(
    user=doctor_user,
    defaults={
        "hospital": hospital,
        "department": cardiology,
        "specialization": "Cardiologist",
        "consultation_fee": 800,
        "experience_years": 8,
        "bio": "Demo cardiologist",
        "registration_number": "DEMO-DR-001",
        "is_verified": True,
        "is_active": True,
    },
)
doctor.hospital = hospital
doctor.department = cardiology
doctor.registration_number = "DEMO-DR-001"
doctor.is_verified = True
doctor.is_active = True
doctor.save()

for wd in range(6):
    DoctorSchedule.objects.get_or_create(
        doctor=doctor,
        weekday=wd,
        start_time=time(9, 0),
        end_time=time(13, 0),
        defaults={"slot_minutes": 20, "is_active": True},
    )

print("Demo accounts:")
print("Application Admin: admin / Admin@123")
print("User: user / User@123")
print("Receptionist: receptionist / Receptionist@123")
print("Doctor: doctor / Doctor@123")
