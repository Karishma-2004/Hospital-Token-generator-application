# Qenova - Hospital Appointment System (Sprints 1-8, complete)

React + Django REST + SQLite. Patients book slots, hospitals run a live queue, doctors write prescriptions, the
application admin approves hospitals, watches the numbers and manages users.

## What each sprint delivered

| Sprint | Delivered |
|---|---|
| 1-2 | Registration, e-mail verification, login (JWT), forgot/reset password, hospital registration |
| 3-4 | Admin approval of hospitals, hospital admin / receptionist / doctor management, schedules, slots, booking, cancel, reschedule |
| 5 | Reception desk: QR scanner (webcam / phone), one-time QR check-in, walk-in tokens, today's list |
| 6 | Doctor dashboard, call-next, live queue board (WebSocket), wait-time estimate, "your turn is near" alert |
| 7 | E-mail + SMS notifications, 24 h / 1 h reminders, online payment (Razorpay or demo), cash at the desk, prescriptions (write, view, PDF download) |
| 8 | Admin dashboard + CSV reports, view / deactivate / delete users, login rate limit, database indexes, 90+ automated tests, production Docker setup |

## Roles
- **Application Admin** - approves hospitals, dashboard, reports, user management.
- **Patient** - books, pays, sees live queue position, downloads prescriptions.
- **Hospital admin** (login role RECEPTIONIST, level HOSPITAL_ADMIN) - adds receptionists, doctors, departments, schedules.
- **Receptionist** - adds doctors/departments/schedules, scans QR, walk-ins, cash payments.
- **Doctor** - queue, call next, prescriptions.

## Run it on Windows (PowerShell)

Backend, first time and after every update:
```powershell
cd backend
pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python seed_demo.py          # only the first time: creates admin / Admin@123 and demo data
.\run_backend.bat            # API + WebSocket on http://localhost:8000
```
Second window - reminders (24 h and 1 h before each visit; leave it open):
```powershell
cd backend
.\run_reminders.bat
```
Third window - frontend:
```powershell
cd frontend
npm install
npm run dev                  # http://localhost:5173
```
Copy `backend/.env.example` to `backend/.env` and put your own e-mail app password there.

## Automated tests
```powershell
cd backend
python manage.py test
```
Covers login/JWT, hospital approval, staff permissions, booking and double-booking, QR check-in (one-time),
walk-ins, the doctor queue and wait estimates, payments (demo and Razorpay signature), prescriptions and who may read
them, e-mail/SMS notifications, reminders (no duplicates), and every admin-panel endpoint.
`TESTING.md` is the manual walk-through for the same flows.

## Configuration (backend/.env)
See `backend/.env.example`. The important ones: `EMAIL_*`, `SMS_PROVIDER` (console or twilio),
`PAYMENT_PROVIDER` (mock or razorpay), `NOTIFY_ASYNC`, `LOGIN_RATE_LIMIT`.

## Go live
See `DEPLOYMENT.md`.

## API map
`/api/auth/*` accounts and JWT - `/api/doctors/*` hospitals, staff, doctors, schedules -
`/api/appointments/*` booking, reception, queue, payments, prescriptions - `/api/admin-panel/*` admin dashboard,
reports, users - `ws://host/ws/queue/<hospital id>/` live queue.
