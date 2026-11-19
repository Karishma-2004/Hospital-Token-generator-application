from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from accounts.models import User
from appointments.models import Appointment, Payment
from doctors.models import Hospital
from .base import (
    BaseCase, PASSWORD, make_appointment, make_doctor, make_hospital, make_receptionist, make_user, rows,
    test_settings,
)


@test_settings
class AdminPanelTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.admin = User.objects.create_superuser("appadmin", "appadmin@example.test", PASSWORD)
        self.hospital, self.hadmin = make_hospital("Alpha Hospital")
        self.doctor = make_doctor(self.hospital, fee=500)
        self.patient = make_user("patient1")

    # ---------------------------------------------------------------- access
    def test_only_application_admin_can_use_the_panel(self):
        urls = ["/api/admin-panel/stats/", "/api/admin-panel/report/", "/api/admin-panel/users/"]
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 401)
        for user in (self.patient, self.hadmin, self.doctor.user):
            self.login_as(user)
            for url in urls:
                self.assertEqual(self.client.get(url).status_code, 403, url)
        self.login_as(self.admin)
        for url in urls:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    # ---------------------------------------------------------------- dashboard
    def test_stats_summarise_users_appointments_and_revenue(self):
        completed = make_appointment(self.patient, self.doctor, at="09:00", status=Appointment.STATUS_COMPLETED)
        make_appointment(self.patient, self.doctor, at="10:00")
        make_appointment(self.patient, self.doctor, at="11:00", status=Appointment.STATUS_CANCELLED)
        Payment.objects.create(appointment=completed, amount=Decimal("500.00"), status="PAID", provider="cash",
                               paid_at=timezone.now())
        self.login_as(self.admin)
        r = self.client.get("/api/admin-panel/stats/?days=7")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["daily"]), 7)
        self.assertEqual(r.data["daily"][-1]["total"], 3)
        self.assertEqual(r.data["daily"][-1]["completed"], 1)
        self.assertEqual(r.data["appointments"]["today"], 2)          # cancelled ones are not counted
        self.assertEqual(r.data["appointments"]["by_status"]["CANCELLED"], 1)
        self.assertEqual(Decimal(r.data["revenue"]["total"]), Decimal("500.00"))
        self.assertEqual(r.data["hospitals"]["by_status"]["APPROVED"], 1)
        self.assertEqual(r.data["users"]["by_role"]["USER"], 1)
        self.assertEqual(r.data["top_hospitals"][0]["name"], "Alpha Hospital")
        self.assertEqual(r.data["top_doctors"][0]["completed"], 1)

    def test_days_parameter_is_clamped(self):
        self.login_as(self.admin)
        self.assertEqual(len(self.client.get("/api/admin-panel/stats/?days=99999").data["daily"]), 365)
        self.assertEqual(len(self.client.get("/api/admin-panel/stats/?days=abc").data["daily"]), 30)

    # ---------------------------------------------------------------- report
    def test_report_per_hospital_and_csv_export(self):
        done = make_appointment(self.patient, self.doctor, at="09:00", status=Appointment.STATUS_COMPLETED)
        make_appointment(None, self.doctor, at="10:00", is_walk_in=True, walk_in_name="Ravi")
        make_appointment(
            self.patient, self.doctor, at="11:00", day=timezone.localdate() - timedelta(days=2)
        )   # still BOOKED two days later = no-show
        Payment.objects.create(appointment=done, amount=Decimal("500"), status="PAID", provider="cash", paid_at=timezone.now())
        self.login_as(self.admin)
        r = self.client.get("/api/admin-panel/report/")
        self.assertEqual(r.status_code, 200)
        row = next(x for x in r.data["rows"] if x["hospital"] == "Alpha Hospital")
        self.assertEqual((row["appointments"], row["completed"], row["walk_ins"], row["no_show"]), (3, 1, 1, 1))
        self.assertEqual(Decimal(row["revenue"]), Decimal("500"))
        csv_response = self.client.get("/api/admin-panel/report/?export=csv")
        self.assertEqual(csv_response.status_code, 200)
        self.assertIn("text/csv", csv_response["Content-Type"])
        text = csv_response.content.decode()
        self.assertIn("Alpha Hospital", text)
        self.assertIn("TOTAL", text)

    def test_report_date_range_filters_and_validates(self):
        make_appointment(self.patient, self.doctor, day=timezone.localdate() - timedelta(days=60))
        self.login_as(self.admin)
        r = self.client.get("/api/admin-panel/report/")
        self.assertEqual(r.data["totals"]["appointments"], 0)
        start = (timezone.localdate() - timedelta(days=61)).isoformat()
        end = (timezone.localdate() - timedelta(days=59)).isoformat()
        wide = self.client.get(f"/api/admin-panel/report/?from={start}&to={end}")
        self.assertEqual(wide.data["totals"]["appointments"], 1)
        self.assertEqual(self.client.get(f"/api/admin-panel/report/?from={end}&to={start}").status_code, 400)

    def test_csv_cells_cannot_run_as_spreadsheet_formulas(self):
        Hospital.objects.filter(pk=self.hospital.pk).update(name="=HYPERLINK(\"http://evil\")")
        self.login_as(self.admin)
        text = self.client.get("/api/admin-panel/report/?export=csv").content.decode()
        self.assertNotIn("\n=HYPERLINK", text)
        self.assertIn("'=HYPERLINK", text)

    # ---------------------------------------------------------------- users
    def test_user_list_filters_and_paginates(self):
        for i in range(8):
            make_user(f"bulk{i}")
        self.login_as(self.admin)
        page1 = self.client.get("/api/admin-panel/users/?page_size=5")
        self.assertEqual(page1.data["pages"], 3)
        self.assertEqual(len(page1.data["results"]), 5)
        self.assertEqual(len(self.client.get("/api/admin-panel/users/?role=DOCTOR").data["results"]), 1)
        found = self.client.get("/api/admin-panel/users/?search=bulk3").data["results"]
        self.assertEqual([u["username"] for u in found], ["bulk3"])
        doc = self.client.get("/api/admin-panel/users/?role=DOCTOR").data["results"][0]
        self.assertEqual(doc["hospital"], "Alpha Hospital")
        self.assertNotIn("password", doc)

    def test_deactivating_a_user_blocks_them_immediately(self):
        self.login_as(self.patient)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)
        self.login_as(self.admin)
        r = self.client.patch(f"/api/admin-panel/users/{self.patient.id}/", {"is_active": False}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(r.data["is_active"])
        self.login_as(self.patient)   # the token is still valid, the account is not
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)
        login = self.client.post("/api/auth/token/", {"username": "patient1", "password": PASSWORD}, format="json")
        self.assertNotEqual(login.status_code, 200)
        self.login_as(self.admin)
        self.client.patch(f"/api/admin-panel/users/{self.patient.id}/", {"is_active": True}, format="json")
        self.login_as(self.patient)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 200)

    def test_deactivating_a_doctor_hides_them_from_patients(self):
        self.login_as(self.admin)
        self.client.patch(f"/api/admin-panel/users/{self.doctor.user.id}/", {"is_active": False}, format="json")
        self.doctor.refresh_from_db()
        self.assertFalse(self.doctor.is_active)
        self.logout()
        self.assertEqual(self.client.get(f"/api/doctors/hospitals/{self.hospital.id}/doctors/").data, [])

    def test_admins_cannot_lock_themselves_or_each_other_out(self):
        other_admin = User.objects.create_superuser("appadmin2", "a2@example.test", PASSWORD)
        self.login_as(self.admin)
        self.assertEqual(
            self.client.patch(f"/api/admin-panel/users/{self.admin.id}/", {"is_active": False}, format="json").status_code, 400
        )
        self.assertEqual(
            self.client.patch(f"/api/admin-panel/users/{other_admin.id}/", {"is_active": False}, format="json").status_code, 403
        )
        self.assertEqual(self.client.delete(f"/api/admin-panel/users/{other_admin.id}/").status_code, 403)

    def test_is_active_must_be_a_boolean(self):
        self.login_as(self.admin)
        r = self.client.patch(f"/api/admin-panel/users/{self.patient.id}/", {"is_active": "yes"}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_delete_user_without_history(self):
        empty = make_user("nohistory")
        self.login_as(self.admin)
        self.assertEqual(self.client.delete(f"/api/admin-panel/users/{empty.id}/").status_code, 204)
        self.assertFalse(User.objects.filter(pk=empty.pk).exists())

    def test_users_with_appointments_cannot_be_deleted(self):
        make_appointment(self.patient, self.doctor)
        self.login_as(self.admin)
        r = self.client.delete(f"/api/admin-panel/users/{self.patient.id}/")
        self.assertEqual(r.status_code, 409)
        self.assertTrue(User.objects.filter(pk=self.patient.pk).exists())
        doctor_delete = self.client.delete(f"/api/admin-panel/users/{self.doctor.user.id}/")
        self.assertEqual(doctor_delete.status_code, 409)
        self.assertTrue(Appointment.objects.exists())

    def test_hospital_admin_account_cannot_be_deleted(self):
        self.login_as(self.admin)
        self.assertEqual(self.client.delete(f"/api/admin-panel/users/{self.hadmin.id}/").status_code, 409)

    def test_unknown_user_is_404(self):
        self.login_as(self.admin)
        self.assertEqual(self.client.delete("/api/admin-panel/users/999999/").status_code, 404)
