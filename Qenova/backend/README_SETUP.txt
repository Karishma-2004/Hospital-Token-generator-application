Qenova backend setup

1. Create backend/.env from backend/.env.example.
2. Set EMAIL_HOST_USER to your Gmail address.
3. Set EMAIL_HOST_PASSWORD to your Gmail 16-character App Password (not your normal Gmail password). You can paste it without spaces.
4. Run:
   python -m pip install -r requirements.txt
   python manage.py migrate
   python manage.py check
   python manage.py runserver

Registration sends a 6-digit verification code. If SMTP fails, the API returns the SMTP error during development and the backend terminal also shows it.

For Gmail, 2-Step Verification must be enabled and an App Password must be created for the account.

----- Sprint 7 and 8 update -----
1. pip install -r requirements.txt
2. python manage.py makemigrations     (creates the new payment, prescription and notification tables)
3. python manage.py migrate
4. run_backend.bat                     (API + live queue)  and  run_reminders.bat  (reminders)
5. python manage.py test               (automated tests)
Put real e-mail, SMS and payment settings in backend/.env (see .env.example).
