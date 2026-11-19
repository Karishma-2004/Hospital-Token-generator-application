from django.test import override_settings

from accounts.models import User
from doctors.models import Hospital, HospitalStaff
from .base import BaseCase, PASSWORD, make_doctor, make_hospital, make_receptionist, make_user, rows, test_settings


@test_settings
class AuthTests(BaseCase):
    def test_login_returns_jwt_and_me_works(self):
        make_user("patient1")
        r = self.client.post("/api/auth/token/", {"username": "patient1", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("access", r.data)
        self.assertIn("refresh", r.data)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['access']}")
        me = self.client.get("/api/auth/me/")
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["username"], "patient1")

    def test_wrong_password_is_rejected(self):
        make_user("patient1")
        r = self.client.post("/api/auth/token/", {"username": "patient1", "password": "nope-nope"}, format="json")
        self.assertEqual(r.status_code, 401)

    def test_protected_endpoints_need_a_token(self):
        self.assertEqual(self.client.get("/api/appointments/").status_code, 401)
        self.assertEqual(self.client.post("/api/doctors/receptionist/departments/", {"name": "X"}).status_code, 401)
        self.assertEqual(self.client.get("/api/admin-panel/stats/").status_code, 401)

    def test_refresh_rotates_and_logout_blacklists(self):
        make_user("patient1")
        tokens = self.client.post("/api/auth/token/", {"username": "patient1", "password": PASSWORD}, format="json").data
        refreshed = self.client.post("/api/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json")
        self.assertEqual(refreshed.status_code, 200)
        new_refresh = refreshed.data["refresh"]
        self.assertEqual(self.client.post("/api/auth/logout/", {"refresh": new_refresh}, format="json").status_code, 205)
        again = self.client.post("/api/auth/token/refresh/", {"refresh": new_refresh}, format="json")
        self.assertEqual(again.status_code, 401)

    def test_unverified_patient_cannot_log_in(self):
        user = make_user("patient2")
        user.email_verified = False
        user.save()
        r = self.client.post("/api/auth/token/", {"username": "patient2", "password": PASSWORD}, format="json")
        self.assertNotEqual(r.status_code, 200)

    def test_login_is_rate_limited(self):
        make_user("patient1")
        codes = [
            self.client.post("/api/auth/token/", {"username": "patient1", "password": "bad-password"}, format="json").status_code
            for _ in range(60)
        ]
        self.assertIn(429, codes)


@test_settings
class HospitalApprovalTests(BaseCase):
    PAYLOAD = {
        "name": "Sunrise Hospital", "registration_number": "TS-HOSP-1", "address": "Plot 21, KPHB",
        "city": "Hyderabad", "state": "Telangana", "pincode": "500072", "phone": "9876543210",
        "email": "contact@sunrise.test", "description": "Multispeciality",
        "admin_name": "Ravi Kumar", "admin_email": "admin@sunrise.test", "admin_password": "Sunrise!2026x",
    }

    def setUp(self):
        super().setUp()
        self.app_admin = User.objects.create_superuser("appadmin", "appadmin@example.test", PASSWORD)

    def register(self):
        r = self.client.post("/api/doctors/hospitals/register/", self.PAYLOAD, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["hospital_id"]

    def login_hospital_admin(self):
        return self.client.post(
            "/api/auth/token/", {"username": "admin@sunrise.test", "password": "Sunrise!2026x"}, format="json"
        )

    def test_pending_hospital_is_hidden_and_cannot_log_in(self):
        hospital_id = self.register()
        self.assertEqual(Hospital.objects.get(id=hospital_id).status, Hospital.STATUS_PENDING)
        listing = self.client.get("/api/doctors/hospitals/")
        self.assertEqual([h["id"] for h in rows(listing)], [])
        self.assertEqual(self.client.get(f"/api/doctors/hospitals/{hospital_id}/").status_code, 404)
        self.assertNotEqual(self.login_hospital_admin().status_code, 200)

    def test_admin_approval_publishes_hospital_and_unlocks_login(self):
        hospital_id = self.register()
        self.login_as(self.app_admin)
        pending = self.client.get("/api/doctors/application-admin/hospitals/?status=PENDING")
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(len(rows(pending)), 1)
        r = self.client.post(
            f"/api/doctors/application-admin/hospitals/{hospital_id}/decision/", {"action": "approve"}, format="json"
        )
        self.assertEqual(r.status_code, 200)
        self.logout()
        self.assertEqual([h["id"] for h in rows(self.client.get("/api/doctors/hospitals/"))], [hospital_id])
        self.assertEqual(self.login_hospital_admin().status_code, 200)

    def test_rejection_keeps_hospital_hidden(self):
        hospital_id = self.register()
        self.login_as(self.app_admin)
        r = self.client.post(
            f"/api/doctors/application-admin/hospitals/{hospital_id}/decision/",
            {"action": "reject", "reason": "Incomplete documents"}, format="json",
        )
        self.assertEqual(r.status_code, 200)
        self.logout()
        self.assertEqual(rows(self.client.get("/api/doctors/hospitals/")), [])
        self.assertNotEqual(self.login_hospital_admin().status_code, 200)

    def test_only_application_admin_can_decide(self):
        hospital_id = self.register()
        patient = make_user("patient1")
        self.login_as(patient)
        r = self.client.post(
            f"/api/doctors/application-admin/hospitals/{hospital_id}/decision/", {"action": "approve"}, format="json"
        )
        self.assertEqual(r.status_code, 403)

    def test_duplicate_registration_number_is_rejected(self):
        self.register()
        second = dict(self.PAYLOAD, admin_email="other@sunrise.test")
        r = self.client.post("/api/doctors/hospitals/register/", second, format="json")
        self.assertEqual(r.status_code, 400)

    def test_public_listing_never_exposes_admin_contact(self):
        hospital, _ = make_hospital()
        r = self.client.get("/api/doctors/hospitals/")
        self.assertNotIn("admin_email", r.data[0] if isinstance(r.data, list) else rows(r)[0])


@test_settings
class StaffAndDoctorTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.hospital, self.hadmin = make_hospital("Alpha Hospital")
        self.other_hospital, self.other_admin = make_hospital("Beta Hospital")

    def create_department(self, name="Cardiology"):
        r = self.client.post("/api/doctors/receptionist/departments/", {"name": name}, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        return r.data["id"]

    def doctor_payload(self, department, **extra):
        data = {
            "first_name": "Asha", "last_name": "Reddy", "email": "asha@alpha.test", "mobile": "9123456780",
            "password": "Doctor!Pass2026", "department": department, "specialization": "Cardiologist",
            "registration_number": "TSMC-1", "consultation_fee": "800", "experience_years": 10, "bio": "MD",
        }
        data.update(extra)
        return data

    def test_hospital_admin_adds_department_doctor_and_schedule(self):
        self.login_as(self.hadmin)
        dept = self.create_department()
        r = self.client.post("/api/doctors/receptionist/doctors/create/", self.doctor_payload(dept), format="json")
        self.assertEqual(r.status_code, 201, r.data)
        doctor_id = r.data["doctor"]["id"]

        # visible to patients straight away, only because the hospital is approved
        self.logout()
        listing = self.client.get(f"/api/doctors/hospitals/{self.hospital.id}/doctors/")
        self.assertEqual([d["id"] for d in listing.data], [doctor_id])
        self.assertNotIn("email", listing.data[0]["user"])

        self.login_as(self.hadmin)
        schedule = {"doctor": doctor_id, "weekday": 0, "start_time": "09:00", "end_time": "13:00", "slot_minutes": 20}
        self.assertEqual(self.client.post("/api/doctors/receptionist/schedules/", schedule, format="json").status_code, 201)
        overlap = dict(schedule, start_time="12:00", end_time="14:00")
        self.assertEqual(self.client.post("/api/doctors/receptionist/schedules/", overlap, format="json").status_code, 400)

    def test_doctor_can_log_in_after_creation(self):
        self.login_as(self.hadmin)
        dept = self.create_department()
        self.client.post("/api/doctors/receptionist/doctors/create/", self.doctor_payload(dept), format="json")
        self.logout()
        r = self.client.post(
            "/api/auth/token/", {"username": "asha@alpha.test", "password": "Doctor!Pass2026"}, format="json"
        )
        self.assertEqual(r.status_code, 200)

    def test_duplicate_doctor_email_or_registration_is_rejected(self):
        self.login_as(self.hadmin)
        dept = self.create_department()
        self.client.post("/api/doctors/receptionist/doctors/create/", self.doctor_payload(dept), format="json")
        same_email = self.doctor_payload(dept, registration_number="TSMC-2")
        self.assertEqual(self.client.post("/api/doctors/receptionist/doctors/create/", same_email, format="json").status_code, 400)
        same_reg = self.doctor_payload(dept, email="other@alpha.test")
        self.assertEqual(self.client.post("/api/doctors/receptionist/doctors/create/", same_reg, format="json").status_code, 400)

    def test_receptionist_can_add_doctor_but_not_receptionists(self):
        receptionist = make_receptionist(self.hospital)
        self.login_as(receptionist)
        dept = self.create_department("Neurology")
        r = self.client.post("/api/doctors/receptionist/doctors/create/", self.doctor_payload(dept), format="json")
        self.assertEqual(r.status_code, 201)
        staff = {"first_name": "New", "email": "new@alpha.test", "password": "Recept!Pass2026"}
        self.assertEqual(self.client.post("/api/doctors/hospital-admin/staff/", staff, format="json").status_code, 403)
        self.login_as(self.hadmin)
        self.assertEqual(self.client.post("/api/doctors/hospital-admin/staff/", staff, format="json").status_code, 201)

    def test_patient_cannot_use_staff_endpoints(self):
        self.login_as(make_user("patient1"))
        self.assertEqual(self.client.get("/api/doctors/receptionist/doctors/").status_code, 403)
        self.assertEqual(self.client.post("/api/doctors/receptionist/departments/", {"name": "X"}).status_code, 403)

    def test_staff_cannot_touch_another_hospitals_doctor(self):
        foreign = make_doctor(self.other_hospital)
        self.login_as(self.hadmin)
        self.assertEqual(rows(self.client.get("/api/doctors/receptionist/doctors/")), [])
        r = self.client.patch(f"/api/doctors/receptionist/doctors/{foreign.id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 404)

    def test_pending_hospital_staff_are_locked_out(self):
        pending, pending_admin = make_hospital("Pending Hospital", approved=False)
        self.login_as(pending_admin)
        self.assertEqual(self.client.get("/api/doctors/receptionist/doctors/").status_code, 403)

    def test_deactivated_doctor_disappears_from_patient_view(self):
        doctor = make_doctor(self.hospital)
        self.login_as(self.hadmin)
        r = self.client.patch(f"/api/doctors/receptionist/doctors/{doctor.id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.logout()
        self.assertEqual(self.client.get(f"/api/doctors/hospitals/{self.hospital.id}/doctors/").data, [])
