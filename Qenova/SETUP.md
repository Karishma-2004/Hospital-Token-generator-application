# Qenova Setup

## 1. Backend

```powershell
cd backend
python -m pip install -r requirements.txt
python manage.py makemigrations
python manage.py migrate
python manage.py check
python manage.py runserver
```

If this is a disposable development database and you are moving from an older incompatible version, delete `backend/db.sqlite3` first and then run `migrate` again.

## 2. Frontend

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## 3. Gmail

The supplied project has Gmail SMTP configured in `backend/.env`.

If you replace the credentials, use a Gmail **App Password**, not the normal Gmail password, and keep it in `.env` only.

## 4. Four-role model

| Role | How created | Approval | Scope |
|---|---|---|---|
| Application Admin | `createsuperuser` | none | all hospitals |
| User | public registration | email verification | public hospital/booking data |
| Hospital admin | hospital registration | Application Admin | one hospital (adds receptionists + doctors) |
| Receptionist | added by hospital admin | none | one hospital (adds doctors) |
| Doctor | added by hospital admin / receptionist | none (auto-verified) | own queue |

## 5. Hospital workflow

1. Hospital representative opens `/hospital-register`.
2. Hospital and administrator information is submitted.
3. A pending hospital is created.
4. Application Admin opens `/admin` and approves/rejects it.
5. On approval, the receptionist account becomes active.
6. The approved hospital becomes visible under `/hospitals`.
7. Hospital admin (or a receptionist) creates departments, doctors and each doctor's weekly schedule.
8. Hospital admin can add receptionist accounts.
9. Doctors appear to patients only inside their own approved hospital.
10. User chooses a doctor and sees the generated schedule slots.
11. Already booked slots are displayed as **Booked** and cannot be selected.
12. Available slots can be booked by a verified user.
13. Booking creates a unique hospital/day token and QR ticket.
