import hashlib
import hmac
from datetime import datetime, time, timedelta
from io import StringIO

from django.core import mail
from django.core.management import call_command
from django.test import override_settings
from django.utils import timezone

from appointments import notify
from appointments.models import Appointment, NotificationLog, Payment, Prescription
from appointments.reminders import run_reminders
from .base import (
    BaseCase, make_appointment, make_doctor, make_hospital, make_receptionist, make_schedule, make_user,
    rows, test_settings, tomorrow,
)


@test_settings
class PaymentTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.hospital, self.hadmin = make_hospital("Alpha")
        self.doctor = make_doctor(self.hospital, fee=500)
        self.patient = make_user("patient1", mobile="9876543210")
        self.other = make_user("patient2")
        self.appointment = make_appointment(self.patient, self.doctor)

    def pay_url(self, suffix=""):
        return f"/api/appointments/{self.appointment.id}/pay/{suffix}"

    def pay_online(self):
        order = self.client.post(self.pay_url())
        self.assertEqual(order.status_code, 200, order.data)
        return order.data

    def test_gateway_config_tells_the_browser_which_provider(self):
        self.login_as(self.patient)
        r = self.client.get("/api/appointments/payments/config/")
        self.assertEqual(r.data["provider"], "mock")

    def test_demo_payment_flow_marks_paid_and_sends_receipt(self):
        self.login_as(self.patient)
        order = self.pay_online()
        self.assertEqual(order["provider"], "mock")
        self.assertEqual(order["amount"], "500.00")
        bad = self.client.post(self.pay_url("verify/"), {"order_id": order["order_id"], "signature": "x"}, format="json")
        self.assertEqual(bad.status_code, 400)
        with self.captureOnCommitCallbacks(execute=True):
            ok = self.client.post(
                self.pay_url("verify/"), {"order_id": order["order_id"], "signature": "mock-signature"}, format="json"
            )
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(Payment.objects.get(appointment=self.appointment).status, "PAID")
        self.assertTrue(any("Payment received" in m.subject for m in mail.outbox))
        listing = rows(self.client.get("/api/appointments/"))
        self.assertEqual(listing[0]["payment_status"], "PAID")
        self.assertEqual(self.client.post(self.pay_url()).status_code, 409)   # cannot pay twice

    def test_verify_with_another_orders_id_is_rejected(self):
        self.login_as(self.patient)
        self.pay_online()
        r = self.client.post(self.pay_url("verify/"), {"order_id": "other-order", "signature": "mock-signature"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertNotEqual(Payment.objects.get(appointment=self.appointment).status, "PAID")

    def test_other_patient_cannot_pay_for_my_appointment(self):
        self.login_as(self.other)
        self.assertEqual(self.client.post(self.pay_url()).status_code, 404)

    def test_free_consultation_needs_no_payment(self):
        self.doctor.consultation_fee = 0
        self.doctor.save()
        self.login_as(self.patient)
        self.assertEqual(self.client.post(self.pay_url()).status_code, 400)
        self.assertEqual(rows(self.client.get("/api/appointments/"))[0]["payment_status"], "NOT_REQUIRED")

    def test_receptionist_records_cash_payment(self):
        receptionist = make_receptionist(self.hospital)
        self.login_as(receptionist)
        r = self.client.post(self.pay_url("cash/"))
        self.assertEqual(r.status_code, 200, r.data)
        payment = Payment.objects.get(appointment=self.appointment)
        self.assertEqual((payment.status, payment.provider), ("PAID", "cash"))
        self.assertEqual(self.client.post(self.pay_url("cash/")).status_code, 409)

    def test_other_hospitals_receptionist_cannot_record_cash(self):
        other_hospital, other_admin = make_hospital("Beta")
        self.login_as(other_admin)
        self.assertEqual(self.client.post(self.pay_url("cash/")).status_code, 404)

    def test_patient_cannot_record_cash(self):
        self.login_as(self.patient)
        self.assertEqual(self.client.post(self.pay_url("cash/")).status_code, 403)

    def test_cancelling_a_paid_appointment_marks_a_refund_due(self):
        self.login_as(self.patient)
        order = self.pay_online()
        self.client.post(self.pay_url("verify/"), {"order_id": order["order_id"], "signature": "mock-signature"}, format="json")
        self.assertEqual(self.client.delete(f"/api/appointments/{self.appointment.id}/").status_code, 204)
        self.assertEqual(Payment.objects.get(appointment=self.appointment).status, "REFUND_DUE")
        self.assertEqual(rows(self.client.get("/api/appointments/"))[0]["payment_status"], "REFUND_DUE")

    @override_settings(PAYMENT_PROVIDER="razorpay", RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="secret123")
    def test_razorpay_signature_is_verified(self):
        Payment.objects.create(
            appointment=self.appointment, amount=500, provider="razorpay", provider_order_id="order_ABC", status="PENDING"
        )
        self.login_as(self.patient)
        forged = self.client.post(self.pay_url("verify/"), {
            "order_id": "order_ABC", "payment_id": "pay_XYZ", "signature": "forged"}, format="json")
        self.assertEqual(forged.status_code, 400)
        self.assertNotEqual(Payment.objects.get(appointment=self.appointment).status, "PAID")
        good_signature = hmac.new(b"secret123", b"order_ABC|pay_XYZ", hashlib.sha256).hexdigest()
        ok = self.client.post(self.pay_url("verify/"), {
            "order_id": "order_ABC", "payment_id": "pay_XYZ", "signature": good_signature}, format="json")
        self.assertEqual(ok.status_code, 200, ok.data)
        self.assertEqual(Payment.objects.get(appointment=self.appointment).status, "PAID")

    @override_settings(PAYMENT_PROVIDER="razorpay", RAZORPAY_KEY_ID="rzp_test_key", RAZORPAY_KEY_SECRET="secret123")
    def test_demo_signature_is_refused_when_razorpay_is_active(self):
        Payment.objects.create(
            appointment=self.appointment, amount=500, provider="mock", provider_order_id="mock_order_1", status="PENDING"
        )
        self.login_as(self.patient)
        r = self.client.post(self.pay_url("verify/"), {"order_id": "mock_order_1", "signature": "mock-signature"}, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertNotEqual(Payment.objects.get(appointment=self.appointment).status, "PAID")


@test_settings
class PrescriptionTests(BaseCase):
    BODY = {
        "diagnosis": "Viral fever", "notes": "Temp 101F", "advice": "Rest and fluids",
        "items": [{"medicine": "Paracetamol 500", "dosage": "1 tablet", "frequency": "1-1-1",
                   "duration": "3 days", "instructions": "after food"}],
    }

    def setUp(self):
        super().setUp()
        self.hospital, self.hadmin = make_hospital("Alpha")
        self.doctor = make_doctor(self.hospital)
        self.patient = make_user("patient1")
        self.appointment = make_appointment(self.patient, self.doctor, status=Appointment.STATUS_IN_CONSULTATION)
        self.url = f"/api/appointments/{self.appointment.id}/prescription/"

    def test_doctor_writes_and_patient_reads_and_gets_an_email(self):
        self.login_as(self.doctor.user)
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.put(self.url, self.BODY, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertTrue(any("prescription is ready" in m.subject for m in mail.outbox))
        self.login_as(self.patient)
        got = self.client.get(self.url)
        self.assertEqual(got.status_code, 200)
        self.assertEqual(got.data["prescription"]["diagnosis"], "Viral fever")
        self.assertEqual(got.data["prescription"]["items"][0]["medicine"], "Paracetamol 500")
        self.assertEqual(got.data["hospital"]["name"], "Alpha")
        self.assertTrue(rows(self.client.get("/api/appointments/"))[0]["has_prescription"])

    def test_updating_replaces_medicines_and_does_not_email_again(self):
        self.login_as(self.doctor.user)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.put(self.url, self.BODY, format="json")
        sent = len(mail.outbox)
        changed = dict(self.BODY, items=[{"medicine": "Cetirizine"}, {"medicine": "ORS"}])
        with self.captureOnCommitCallbacks(execute=True):
            r = self.client.put(self.url, changed, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["prescription"]["items"]), 2)
        self.assertEqual(Prescription.objects.count(), 1)
        self.assertEqual(len(mail.outbox), sent)

    def test_only_the_treating_doctor_can_write(self):
        self.login_as(self.patient)
        self.assertEqual(self.client.put(self.url, self.BODY, format="json").status_code, 403)
        self.login_as(self.hadmin)
        self.assertEqual(self.client.put(self.url, self.BODY, format="json").status_code, 403)
        other_doctor = make_doctor(self.hospital)
        self.login_as(other_doctor.user)
        self.assertEqual(self.client.put(self.url, self.BODY, format="json").status_code, 404)

    def test_cannot_write_before_the_patient_is_called_in(self):
        self.appointment.status = Appointment.STATUS_BOOKED
        self.appointment.save()
        self.login_as(self.doctor.user)
        self.assertEqual(self.client.put(self.url, self.BODY, format="json").status_code, 400)

    def test_diagnosis_is_required(self):
        self.login_as(self.doctor.user)
        r = self.client.put(self.url, {"items": []}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_private_to_patient_and_doctor(self):
        self.login_as(self.doctor.user)
        self.client.put(self.url, self.BODY, format="json")
        self.assertEqual(self.client.get(self.url).status_code, 200)       # the doctor can read it back
        for stranger in (make_user("patient2"), self.hadmin, make_doctor(self.hospital).user):
            self.login_as(stranger)
            self.assertEqual(self.client.get(self.url).status_code, 404)

    def test_missing_prescription_is_404(self):
        self.login_as(self.patient)
        self.assertEqual(self.client.get(self.url).status_code, 404)


@test_settings
class NotificationTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.hospital, self.hadmin = make_hospital("Alpha")
        self.doctor = make_doctor(self.hospital)
        self.day = tomorrow()
        make_schedule(self.doctor, self.day.weekday(), "09:00", "10:00", 15)
        self.patient = make_user("patient1", mobile="98765 43210")

    def test_normalize_mobile(self):
        self.assertEqual(notify.normalize_mobile("98765 43210"), "+919876543210")
        self.assertEqual(notify.normalize_mobile("+14155550100"), "+14155550100")
        self.assertEqual(notify.normalize_mobile("123"), "")
        self.assertEqual(notify.normalize_mobile(""), "")

    def book(self):
        self.login_as(self.patient)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post("/api/appointments/", {
                "doctor": self.doctor.id, "appointment_date": self.day.isoformat(), "appointment_time": "09:00",
            }, format="json")

    def test_booking_sends_email_and_sms_and_logs_them(self):
        r = self.book()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("confirmed", mail.outbox[0].subject)
        self.assertEqual(mail.outbox[0].to, ["patient1@example.test"])
        logs = {(n.channel, n.status) for n in NotificationLog.objects.filter(kind="BOOKED")}
        self.assertEqual(logs, {("EMAIL", "SENT"), ("SMS", "SENT")})

    def test_missing_mobile_number_skips_sms_without_failing(self):
        self.patient.mobile = ""
        self.patient.save()
        self.assertEqual(self.book().status_code, 201)
        sms = NotificationLog.objects.get(kind="BOOKED", channel="SMS")
        self.assertEqual(sms.status, "SKIPPED")

    def test_cancel_and_reschedule_send_emails(self):
        appointment_id = self.book().data["id"]
        with self.captureOnCommitCallbacks(execute=True):
            self.client.put(f"/api/appointments/{appointment_id}/", {
                "appointment_date": self.day.isoformat(), "appointment_time": "09:30"}, format="json")
        with self.captureOnCommitCallbacks(execute=True):
            self.client.delete(f"/api/appointments/{appointment_id}/")
        subjects = " | ".join(m.subject for m in mail.outbox)
        self.assertIn("rescheduled", subjects)
        self.assertIn("cancelled", subjects)

    def test_a_failing_email_server_does_not_break_booking(self):
        with override_settings(EMAIL_BACKEND="tests.test_payments_prescriptions_notifications.BrokenBackend"):
            r = self.book()
        self.assertEqual(r.status_code, 201)
        self.assertTrue(NotificationLog.objects.filter(kind="BOOKED", channel="EMAIL", status="FAILED").exists())


from django.core.mail.backends.base import BaseEmailBackend  # noqa: E402


class BrokenBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        raise ConnectionError("SMTP is down")


@test_settings
class ReminderTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.hospital, self.hadmin = make_hospital("Alpha")
        self.doctor = make_doctor(self.hospital)
        self.patient = make_user("patient1", mobile="9876543210")
        self.day = tomorrow()
        self.start = timezone.make_aware(datetime.combine(self.day, time(10, 0)))
        self.appointment = make_appointment(self.patient, self.doctor, day=self.day, at="10:00")

    def booked_ago(self, delta):
        Appointment.objects.filter(pk=self.appointment.pk).update(created_at=self.start - delta)

    def run_at(self, moment):
        with self.captureOnCommitCallbacks(execute=True):
            return run_reminders(now=moment)

    def test_one_hour_reminder_goes_out_once(self):
        self.booked_ago(timedelta(days=3))
        first = self.run_at(self.start - timedelta(minutes=30))
        self.assertEqual(first, {"24h": 0, "1h": 1})
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("1 hour", mail.outbox[0].subject)
        again = self.run_at(self.start - timedelta(minutes=29))
        self.assertEqual(again, {"24h": 0, "1h": 0})
        self.assertEqual(len(mail.outbox), 1)

    def test_twenty_four_hour_reminder_goes_out_once(self):
        self.booked_ago(timedelta(days=3))
        first = self.run_at(self.start - timedelta(hours=23))
        self.assertEqual(first, {"24h": 1, "1h": 0})
        self.assertIn("tomorrow", mail.outbox[0].subject)
        self.assertEqual(self.run_at(self.start - timedelta(hours=22)), {"24h": 0, "1h": 0})

    def test_both_reminders_are_sent_for_the_same_visit(self):
        self.booked_ago(timedelta(days=3))
        self.run_at(self.start - timedelta(hours=23))
        self.run_at(self.start - timedelta(minutes=30))
        self.assertEqual(len(mail.outbox), 2)
        self.assertEqual(NotificationLog.objects.filter(channel="SMS", status="SENT").count(), 2)

    def test_no_24h_reminder_for_a_last_minute_booking(self):
        self.booked_ago(timedelta(hours=2))
        self.assertEqual(self.run_at(self.start - timedelta(hours=20)), {"24h": 0, "1h": 0})
        self.assertEqual(mail.outbox, [])

    def test_nothing_is_sent_too_early_or_for_cancelled_or_checked_in(self):
        self.booked_ago(timedelta(days=3))
        self.assertEqual(self.run_at(self.start - timedelta(hours=30)), {"24h": 0, "1h": 0})
        self.appointment.status = Appointment.STATUS_CANCELLED
        self.appointment.save()
        self.assertEqual(self.run_at(self.start - timedelta(minutes=30)), {"24h": 0, "1h": 0})
        self.appointment.status = Appointment.STATUS_CHECKED_IN
        self.appointment.save()
        self.assertEqual(self.run_at(self.start - timedelta(minutes=30)), {"24h": 0, "1h": 0})
        self.assertEqual(mail.outbox, [])

    def test_a_rescheduled_visit_gets_fresh_reminders(self):
        self.booked_ago(timedelta(days=3))
        self.run_at(self.start - timedelta(minutes=30))
        Appointment.objects.filter(pk=self.appointment.pk).update(appointment_time=time(11, 0))
        new_start = self.start + timedelta(hours=1)
        self.assertEqual(self.run_at(new_start - timedelta(minutes=30)), {"24h": 0, "1h": 1})

    def test_management_command_runs(self):
        out = StringIO()
        call_command("send_reminders", stdout=out)
        self.assertIn("Reminders sent", out.getvalue())
