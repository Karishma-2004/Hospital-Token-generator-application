# Going live

## 1. Fill in backend/.env for production
```
DJANGO_DEBUG=False
DJANGO_SECRET_KEY=<long random value>          # python -c "import secrets; print(secrets.token_urlsafe(64))"
DJANGO_ALLOWED_HOSTS=your-domain.example
CORS_ALLOWED_ORIGINS=https://your-domain.example
CSRF_TRUSTED_ORIGINS=https://your-domain.example
FRONTEND_URL=https://your-domain.example
PAYMENT_PROVIDER=razorpay
RAZORPAY_KEY_ID=...
RAZORPAY_KEY_SECRET=...
SMS_PROVIDER=twilio            # or keep console and do not promise SMS
EMAIL_HOST_USER / EMAIL_HOST_PASSWORD / DEFAULT_FROM_EMAIL
```
With `DJANGO_DEBUG=False` the server refuses to start if the secret key is the default or if
`PAYMENT_PROVIDER` is still `mock` (so nobody can "pay" for free by accident).

## 2. Build and start
```
docker compose -f docker-compose.prod.yml up --build -d
```
Three containers: the API (migrates the database on start), the reminder sender, and nginx serving the React build and
forwarding `/api` and `/ws` to the API. Put HTTPS (a reverse proxy or your host's load balancer) in front of port 80.
The browser camera used by the reception desk only works on HTTPS or localhost.

## 3. Create the first admin
```
docker compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser
```

## 4. Backups and limits
- The database is one SQLite file in the `medibook-data` volume. Back it up daily (copy `/data/db.sqlite3`).
- Run ONE API worker: the live-queue WebSocket layer keeps its state in memory. To scale out, switch
  `CHANNEL_LAYERS` to Redis (`channels-redis`) first.
- SQLite suits one hospital group at this size. For many hospitals moving to PostgreSQL is the next step.
- Refunds: cancelling a paid visit marks the payment "Refund due". The hospital refunds it in the Razorpay dashboard.

## 5. Final checks before opening to patients
`python manage.py test` passes, `python manage.py check --deploy` shows no warnings you do not understand, a test
booking sends a real e-mail, and one real small payment goes through and shows as Paid.
