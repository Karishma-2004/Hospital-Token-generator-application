from datetime import timedelta

from django.utils import timezone

from appointments.models import Appointment
from .base import (
    BaseCase, make_appointment, make_doctor, make_hospital, make_receptionist, make_schedule, make_user,
    rows, test_settings, tomorrow,
)


@test_settings
class BookingTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.hospital, self.hadmin = make_hospital()
        self.doctor = make_doctor(self.hospital)
        self.day = tomorrow()
        make_schedule(self.doctor, self.day.weekday(), "09:00", "10:00", 15)
        self.patient = make_user("patient1")
        self.other = make_user("patient2")

    def book(self, time="09:00", doctor=None):
        return self.client.post("/api/appointments/", {
            "doctor": (doctor or self.doctor).id, "appointment_date": self.day.isoformat(), "appointment_time": time,
        }, format="json")

    def test_slots_are_listed_publicly(self):
        r = self.client.get(f"/api/appointments/doctors/{self.doctor.id}/slots/?date={self.day.isoformat()}")
        self.assertEqual(r.status_code, 200)
        self.assertEqual([s["start_time"] for s in r.data["slots"]], ["09:00", "09:15", "09:30", "09:45"])
        self.assertTrue(all(s["status"] == "AVAILABLE" for s in r.data["slots"]))

    def test_booking_gives_token_and_one_time_qr(self):
        self.login_as(self.patient)
        r = self.book()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["token_number"], 1)
        self.assertEqual(r.data["status"], "BOOKED")
        self.assertTrue(r.data["qr_payload"].startswith(f"MB1:{r.data['id']}:"))

    def test_double_booking_the_same_slot_is_blocked(self):
        self.login_as(self.patient)
        self.assertEqual(self.book().status_code, 201)
        self.login_as(self.other)
        self.assertEqual(self.book().status_code, 409)
        slots = self.client.get(f"/api/appointments/doctors/{self.doctor.id}/slots/?date={self.day.isoformat()}")
        self.assertEqual(slots.data["slots"][0]["status"], "BOOKED")

    def test_invalid_times_and_unavailable_doctors_are_rejected(self):
        self.login_as(self.patient)
        self.assertEqual(self.book("09:07").status_code, 400)       # not on the slot grid
        self.assertEqual(self.book("11:00").status_code, 400)       # outside the schedule
        pending, _ = make_hospital("Pending", approved=False)
        hidden = make_doctor(pending)
        make_schedule(hidden, self.day.weekday())
        self.assertEqual(self.book(doctor=hidden).status_code, 400)

    def test_past_slots_cannot_be_booked(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self.login_as(self.patient)
        r = self.client.post("/api/appointments/", {
            "doctor": self.doctor.id, "appointment_date": yesterday.isoformat(), "appointment_time": "09:00",
        }, format="json")
        self.assertEqual(r.status_code, 400)

    def test_only_patients_book_and_patients_see_only_their_own(self):
        self.login_as(self.patient)
        self.book()
        self.login_as(self.other)
        self.assertEqual(rows(self.client.get("/api/appointments/")), [])
        self.login_as(self.hadmin)
        self.assertEqual(self.book().status_code, 403)

    def test_cancel_frees_the_slot_and_reschedule_moves_it(self):
        self.login_as(self.patient)
        appointment_id = self.book().data["id"]
        moved = self.client.put(f"/api/appointments/{appointment_id}/", {
            "appointment_date": self.day.isoformat(), "appointment_time": "09:30",
        }, format="json")
        self.assertEqual(moved.status_code, 200, moved.data)
        self.assertEqual(Appointment.objects.get(id=appointment_id).appointment_time.strftime("%H:%M"), "09:30")
        self.assertEqual(self.client.delete(f"/api/appointments/{appointment_id}/").status_code, 204)
        self.assertEqual(Appointment.objects.get(id=appointment_id).status, "CANCELLED")
        self.login_as(self.other)
        self.assertEqual(self.book("09:30").status_code, 201)

    def test_other_patient_cannot_cancel_my_appointment(self):
        self.login_as(self.patient)
        appointment_id = self.book().data["id"]
        self.login_as(self.other)
        self.assertEqual(self.client.delete(f"/api/appointments/{appointment_id}/").status_code, 404)

    def test_old_booking_without_qr_code_gets_one(self):
        appointment = make_appointment(self.patient, self.doctor, day=self.day, checkin_code=None)
        self.login_as(self.patient)
        r = self.client.get("/api/appointments/")
        self.assertTrue(rows(r)[0]["qr_payload"].startswith("MB1:"))
        appointment.refresh_from_db()
        self.assertTrue(appointment.checkin_code)


@test_settings
class ReceptionTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.hospital, self.hadmin = make_hospital("Alpha")
        self.receptionist = make_receptionist(self.hospital)
        self.doctor = make_doctor(self.hospital)
        self.patient = make_user("patient1")
        self.other_hospital, self.other_admin = make_hospital("Beta")

    def scan(self, appointment, code=None):
        return self.client.post("/api/appointments/reception/scan/", {
            "payload": f"MB1:{appointment.id}:{code or appointment.checkin_code}"
        }, format="json")

    def test_qr_checks_a_patient_in_exactly_once(self):
        appointment = make_appointment(self.patient, self.doctor)
        self.login_as(self.receptionist)
        first = self.scan(appointment)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["appointment"]["status"], "CHECKED_IN")
        appointment.refresh_from_db()
        self.assertIsNotNone(appointment.checked_in_at)
        second = self.scan(appointment)
        self.assertEqual(second.status_code, 409)
        self.assertIn("already used", second.data["detail"])

    def test_bad_qr_codes_are_rejected(self):
        appointment = make_appointment(self.patient, self.doctor)
        self.login_as(self.receptionist)
        self.assertEqual(self.scan(appointment, code="wrong-code").status_code, 404)
        self.assertEqual(
            self.client.post("/api/appointments/reception/scan/", {"payload": "hello"}, format="json").status_code, 400
        )

    def test_qr_of_another_hospital_is_rejected(self):
        appointment = make_appointment(self.patient, self.doctor)
        self.login_as(self.other_admin)
        self.assertEqual(self.scan(appointment).status_code, 404)

    def test_qr_for_another_day_or_cancelled_booking_is_rejected(self):
        later = make_appointment(self.patient, self.doctor, day=timezone.localdate() + timedelta(days=1))
        cancelled = make_appointment(self.patient, self.doctor, at="11:00", status=Appointment.STATUS_CANCELLED)
        self.login_as(self.receptionist)
        self.assertEqual(self.scan(later).status_code, 400)
        self.assertEqual(self.scan(cancelled).status_code, 400)

    def test_patient_cannot_scan(self):
        appointment = make_appointment(self.patient, self.doctor)
        self.login_as(self.patient)
        self.assertEqual(self.scan(appointment).status_code, 403)

    def test_manual_check_in_without_qr(self):
        appointment = make_appointment(self.patient, self.doctor)
        self.login_as(self.receptionist)
        r = self.client.post(f"/api/appointments/{appointment.id}/status/", {"status": "CHECKED_IN"}, format="json")
        self.assertEqual(r.status_code, 200)
        appointment.refresh_from_db()
        self.assertEqual(appointment.status, "CHECKED_IN")

    def test_walk_in_gets_next_token_and_joins_queue(self):
        make_appointment(self.patient, self.doctor)  # token 1
        self.login_as(self.receptionist)
        r = self.client.post("/api/appointments/reception/walk-in/", {
            "doctor": self.doctor.id, "name": "Ravi Kumar", "phone": "9876543210",
        }, format="json")
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["appointment"]["token_number"], 2)
        walk_in = Appointment.objects.get(id=r.data["appointment"]["id"])
        self.assertTrue(walk_in.is_walk_in)
        self.assertIsNone(walk_in.patient)
        self.assertEqual(walk_in.status, "CHECKED_IN")
        again = self.client.post("/api/appointments/reception/walk-in/", {"doctor": self.doctor.id, "name": "Sita"}, format="json")
        self.assertEqual(again.status_code, 201)
        self.assertEqual(again.data["appointment"]["token_number"], 3)

    def test_walk_in_validation(self):
        foreign = make_doctor(self.other_hospital)
        self.login_as(self.receptionist)
        url = "/api/appointments/reception/walk-in/"
        self.assertEqual(self.client.post(url, {"doctor": self.doctor.id, "name": ""}, format="json").status_code, 400)
        self.assertEqual(self.client.post(url, {"doctor": foreign.id, "name": "Ravi"}, format="json").status_code, 400)
        self.assertEqual(
            self.client.post(url, {"doctor": self.doctor.id, "name": "Ravi", "phone": "abc"}, format="json").status_code, 400
        )

    def test_todays_list_is_scoped_to_the_hospital(self):
        make_appointment(self.patient, self.doctor)
        foreign_doctor = make_doctor(self.other_hospital)
        make_appointment(self.patient, foreign_doctor)
        self.login_as(self.receptionist)
        r = self.client.get("/api/appointments/reception/today/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["appointments"]), 1)
        self.assertEqual(r.data["counts"]["booked"], 1)
        self.assertEqual(r.data["hospital"]["id"], self.hospital.id)
        self.assertEqual([d["id"] for d in r.data["doctors"]], [self.doctor.id])


@test_settings
class QueueTests(BaseCase):
    def setUp(self):
        super().setUp()
        self.hospital, self.hadmin = make_hospital()
        self.doctor = make_doctor(self.hospital)
        self.now = timezone.now()
        self.patients = [make_user(f"queuepatient{i}") for i in range(4)]
        self.waiting = []
        for i, patient in enumerate(self.patients):   # checked in 5, 4, 3, 2 minutes ago
            self.waiting.append(make_appointment(
                patient, self.doctor, at=f"1{i}:00", status=Appointment.STATUS_CHECKED_IN,
                checked_in_at=self.now - timedelta(minutes=5 - i),
            ))

    def queue(self):
        return self.client.get("/api/appointments/doctor/queue/")

    def test_doctor_sees_queue_in_check_in_order(self):
        self.login_as(self.doctor.user)
        r = self.queue()
        self.assertEqual(r.status_code, 200)
        self.assertEqual([w["token_number"] for w in r.data["waiting"]], [a.token_number for a in self.waiting])
        self.assertIsNone(r.data["current"])

    def test_call_next_runs_the_queue_in_order(self):
        self.login_as(self.doctor.user)
        first = self.client.post("/api/appointments/doctor/call-next/")
        self.assertEqual(first.data["called"]["token_number"], self.waiting[0].token_number)
        self.assertEqual(self.queue().data["current"]["token_number"], self.waiting[0].token_number)
        second = self.client.post("/api/appointments/doctor/call-next/")
        self.assertEqual(second.data["called"]["token_number"], self.waiting[1].token_number)
        self.waiting[0].refresh_from_db()
        self.assertEqual(self.waiting[0].status, "COMPLETED")
        self.assertIsNotNone(self.waiting[0].completed_at)
        self.assertEqual(self.queue().data["completed_count"], 1)

    def test_complete_without_calling_anyone_new(self):
        self.login_as(self.doctor.user)
        self.client.post("/api/appointments/doctor/call-next/")
        self.assertEqual(self.client.post("/api/appointments/doctor/complete/").status_code, 200)
        self.assertIsNone(self.queue().data["current"])
        self.assertEqual(len(self.queue().data["waiting"]), 3)

    def test_call_next_with_empty_queue(self):
        Appointment.objects.update(status="COMPLETED")
        self.login_as(self.doctor.user)
        r = self.client.post("/api/appointments/doctor/call-next/")
        self.assertEqual(r.status_code, 200)
        self.assertIsNone(r.data["called"])

    def test_another_doctor_has_a_separate_queue(self):
        other = make_doctor(self.hospital)
        self.login_as(other.user)
        self.assertEqual(self.queue().data["waiting"], [])

    def test_only_doctors_use_the_doctor_queue(self):
        self.login_as(self.patients[0])
        self.assertEqual(self.queue().status_code, 403)
        self.login_as(self.hadmin)
        self.assertEqual(self.queue().status_code, 403)
        self.logout()
        self.assertEqual(self.queue().status_code, 401)

    def add_history(self, minutes=10, count=2):
        for i in range(count):
            make_appointment(
                make_user(f"history{i}"), self.doctor, at=f"0{i}:30", status=Appointment.STATUS_COMPLETED,
                called_at=self.now - timedelta(minutes=60 + i * 20),
                completed_at=self.now - timedelta(minutes=60 + i * 20 - minutes),
            )

    def info_for(self, patient):
        self.login_as(patient)
        return self.client.get("/api/appointments/my-queue/").data["items"][0]

    def test_wait_time_estimate_and_near_alert(self):
        self.add_history(minutes=10)       # the doctor averages 10 minutes per patient
        last = self.info_for(self.patients[3])
        self.assertEqual(last["patients_ahead"], 3)
        self.assertEqual(last["estimated_wait_minutes"], 30)
        self.assertFalse(last["near"])
        third = self.info_for(self.patients[2])
        self.assertEqual(third["patients_ahead"], 2)
        self.assertEqual(third["estimated_wait_minutes"], 20)
        self.assertTrue(third["near"])

    def test_alert_updates_when_the_doctor_calls_patients(self):
        self.add_history(minutes=10)
        self.login_as(self.doctor.user)
        self.client.post("/api/appointments/doctor/call-next/")
        first = self.info_for(self.patients[0])
        self.assertTrue(first["your_turn"])
        fourth = self.info_for(self.patients[3])
        self.assertEqual(fourth["patients_ahead"], 3)      # one inside + two waiting
        self.assertIn(fourth["estimated_wait_minutes"], (29, 30))
        self.assertEqual(fourth["now_serving"], self.waiting[0].token_number)

    def test_my_queue_only_lists_my_own_appointments_today(self):
        self.login_as(self.patients[0])
        items = self.client.get("/api/appointments/my-queue/").data["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["token_number"], self.waiting[0].token_number)

    def test_public_board_shows_tokens_but_no_patient_names(self):
        self.login_as(self.doctor.user)
        self.client.post("/api/appointments/doctor/call-next/")
        self.logout()
        r = self.client.get(f"/api/appointments/queue-board/{self.hospital.id}/")
        self.assertEqual(r.status_code, 200)
        board = r.data["doctors"][0]
        self.assertEqual(board["now_serving"], self.waiting[0].token_number)
        self.assertEqual(board["waiting"], [a.token_number for a in self.waiting[1:]])
        self.assertNotIn("queuepatient", str(r.data).lower())

    def test_board_of_unapproved_hospital_is_hidden(self):
        pending, _ = make_hospital("Pending", approved=False)
        self.assertEqual(self.client.get(f"/api/appointments/queue-board/{pending.id}/").status_code, 404)
