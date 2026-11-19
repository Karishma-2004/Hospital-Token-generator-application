"""E-mail alert to the Application Admin(s) when a hospital registers and waits for approval."""
import threading

from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Q

from accounts.models import User


def notify_admins_of_registration(hospital):
    emails = list(
        User.objects.filter(is_active=True)
        .filter(Q(is_superuser=True) | Q(role=User.ROLE_ADMIN))
        .exclude(email="")
        .values_list("email", flat=True)
        .distinct()
    )
    if not emails:
        return
    subject = f"New hospital waiting for approval: {hospital.name}"
    body = (
        "A new hospital has registered on Qenova and needs your approval.\n\n"
        f"Hospital: {hospital.name}\n"
        f"City: {hospital.city}, {hospital.state}\n"
        f"Registration number: {hospital.registration_number}\n"
        f"Phone: {hospital.phone}\n"
        f"Email: {hospital.email}\n\n"
        f"Review it here: {settings.FRONTEND_URL.rstrip('/')}/admin\n"
    )

    def send():
        send_mail(subject, body, getattr(settings, "DEFAULT_FROM_EMAIL", None) or None, emails, fail_silently=True)

    if getattr(settings, "NOTIFY_ASYNC", True):
        threading.Thread(target=send, daemon=True).start()   # no database work inside, so no connection to close
    else:
        send()