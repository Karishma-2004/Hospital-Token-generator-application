"""Email and SMS notifications (Sprint 7).

Every message is written to NotificationLog. Sending never breaks the request that
triggered it: errors are logged and stored, not raised.

Settings (all optional, read from .env):
    NOTIFY_ASYNC            send in a background thread (default True)
    SMS_PROVIDER            "console" (default: prints to the server log) or "twilio"
    SMS_DEFAULT_COUNTRY_CODE  added to 10-digit numbers, default "+91"
    TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER
"""
import base64
import logging
import re
import threading
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail import send_mail
from django.db import connection, transaction

from .models import NotificationLog
from .payments import fee_for

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------- low level senders
def normalize_mobile(raw):
    """'98765 43210' -> '+919876543210'. Returns '' when the number looks invalid."""
    digits = re.sub(r"[^\d+]", "", raw or "")
    if not digits:
        return ""
    if digits.startswith("+"):
        return digits if 8 <= len(digits) <= 16 else ""
    digits = digits.lstrip("0")
    if len(digits) == 10:
        return getattr(settings, "SMS_DEFAULT_COUNTRY_CODE", "+91") + digits
    return ""


def _send_email(to, subject, body):
    send_mail(subject, body, getattr(settings, "DEFAULT_FROM_EMAIL", None) or None, [to], fail_silently=False)


def _send_sms(to, text):
    provider = getattr(settings, "SMS_PROVIDER", "console")
    if provider == "twilio":
        sid = getattr(settings, "TWILIO_ACCOUNT_SID", "")
        token = getattr(settings, "TWILIO_AUTH_TOKEN", "")
        sender = getattr(settings, "TWILIO_FROM_NUMBER", "")
        if not (sid and token and sender):
            raise RuntimeError("Twilio is not configured (TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN / TWILIO_FROM_NUMBER).")
        data = urllib.parse.urlencode({"To": to, "From": sender, "Body": text}).encode()
        request = urllib.request.Request(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json", data=data, method="POST"
        )
        auth = base64.b64encode(f"{sid}:{token}".encode()).decode()
        request.add_header("Authorization", f"Basic {auth}")
        try:
            urllib.request.urlopen(request, timeout=15).read()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"Twilio rejected the message (HTTP {e.code}).") from e
    else:
        logger.info("SMS (console provider) to %s: %s", to, text)


# ---------------------------------------------------------------- delivery + log
def _log(appointment_id, kind, channel, recipient, status, error="", key=None):
    NotificationLog.objects.create(
        appointment_id=appointment_id, kind=kind, channel=channel, recipient=recipient[:254],
        status=status, error=error[:300], dedupe_key=key,
    )


def _deliver(appointment_id, kind, email, mobile, subject, body, sms_text, dedupe):
    """Runs in a background thread (or inline). Takes only plain values."""
    channels = [
        (NotificationLog.CHANNEL_EMAIL, email, lambda: _send_email(email, subject, body)),
        (NotificationLog.CHANNEL_SMS, normalize_mobile(mobile), None),
    ]
    for channel, recipient, sender in channels:
        key = f"{dedupe}:{channel}" if dedupe else None
        if key and NotificationLog.objects.filter(dedupe_key=key).exists():
            continue  # this channel already went out (a retry only repeats the one that failed)
        if channel == NotificationLog.CHANNEL_SMS:
            sender = (lambda r=recipient: _send_sms(r, sms_text)) if recipient and sms_text else None
        if not recipient or sender is None:
            _log(appointment_id, kind, channel, recipient or "", NotificationLog.STATUS_SKIPPED,
                 "No address on file." if not recipient else "No SMS text.", key)
            continue
        try:
            sender()
            _log(appointment_id, kind, channel, recipient, NotificationLog.STATUS_SENT, "", key)
        except Exception as exc:  # noqa: BLE001 - a failed notification must never crash anything
            logger.warning("%s %s to %s failed: %s", kind, channel, recipient, exc)
            _log(appointment_id, kind, channel, recipient, NotificationLog.STATUS_FAILED, str(exc))


def _thread_target(*args):
    try:
        _deliver(*args)
    except Exception:  # noqa: BLE001
        logger.exception("Notification thread crashed")
    finally:
        connection.close()


def _dispatch(args, sync):
    if sync or not getattr(settings, "NOTIFY_ASYNC", True):
        _deliver(*args)
    else:
        threading.Thread(target=_thread_target, args=args, daemon=True).start()


def notify_patient(appointment, kind, subject, body, sms_text="", dedupe=None, sync=False):
    """Queue an email + SMS to the patient (or the walk-in's phone). Returns False if skipped
    because the same dedupe key was already handled or failed 3 times."""
    if dedupe:
        done = NotificationLog.objects.filter(
            dedupe_key__in=[f"{dedupe}:{NotificationLog.CHANNEL_EMAIL}", f"{dedupe}:{NotificationLog.CHANNEL_SMS}"]
        ).count()
        if done >= 2:
            return False
        if NotificationLog.objects.filter(
            appointment_id=appointment.id, kind=kind, status=NotificationLog.STATUS_FAILED
        ).count() >= 3:
            return False
    if appointment.patient_id:
        email, mobile = appointment.patient.email, appointment.patient.mobile
    else:
        email, mobile = "", appointment.walk_in_phone
    args = (appointment.id, kind, email, mobile, subject, body, sms_text, dedupe)
    transaction.on_commit(lambda: _dispatch(args, sync))
    return True


# ---------------------------------------------------------------- message templates
def _when(a):
    return f"{a.appointment_date.strftime('%d %b %Y')} at {a.appointment_time.strftime('%I:%M %p').lstrip('0')}"


def _who(a):
    d = a.doctor
    return f"Dr. {d.user.first_name} {d.user.last_name}".strip()


def _greeting(a):
    if a.patient_id:
        return f"Hello {a.patient.first_name or a.patient.username},"
    return f"Hello {a.walk_in_name or 'there'},"


def booking_confirmed(a):
    fee = fee_for(a)
    if fee > 0:
        qr_line = f"Pay the consultation fee (INR {fee}) in 'My Appointments' to get your QR ticket for check-in."
    else:
        qr_line = "Show the QR ticket from 'My Appointments' at the reception desk."
    notify_patient(
        a, "BOOKED", "Your Qenova appointment is confirmed",
        f"{_greeting(a)}\n\nYour appointment is confirmed.\n\nDoctor: {_who(a)}\nHospital: {a.hospital.name}\n"
        f"When: {_when(a)}\nToken: #{a.token_number}\n\n{qr_line}\n\n- Qenova",
        f"Qenova: appointment confirmed with {_who(a)} on {_when(a)}. Token #{a.token_number}.",
    )


def booking_rescheduled(a):
    notify_patient(
        a, "RESCHEDULED", "Your Qenova appointment was rescheduled",
        f"{_greeting(a)}\n\nYour appointment with {_who(a)} at {a.hospital.name} is now on {_when(a)}.\n"
        f"Token: #{a.token_number}\n\n- Qenova",
        f"Qenova: appointment moved to {_when(a)} with {_who(a)}. Token #{a.token_number}.",
    )


def booking_cancelled(a, refund_due=False):
    extra = "\nYour payment will be refunded by the hospital." if refund_due else ""
    notify_patient(
        a, "CANCELLED", "Your Qenova appointment was cancelled",
        f"{_greeting(a)}\n\nYour appointment with {_who(a)} at {a.hospital.name} on {_when(a)} was cancelled.{extra}\n\n- Qenova",
        f"Qenova: appointment with {_who(a)} on {_when(a)} was cancelled.",
    )


def payment_received(a, payment):
    notify_patient(
        a, "PAYMENT", "Payment received - Qenova",
        f"{_greeting(a)}\n\nWe received {payment.currency} {payment.amount} for your appointment with {_who(a)} "
        f"on {_when(a)}.\nReference: {payment.provider_payment_id or payment.provider}\n\n- Qenova",
        f"Qenova: payment of {payment.currency} {payment.amount} received for token #{a.token_number}.",
    )


def prescription_ready(a):
    notify_patient(
        a, "PRESCRIPTION", "Your prescription is ready - Qenova",
        f"{_greeting(a)}\n\n{_who(a)} has added your prescription. Sign in to Qenova and open "
        f"'My Appointments' to view or download it.\n\n- Qenova",
        f"Qenova: your prescription from {_who(a)} is ready in My Appointments.",
    )


def reminder(a, hours, dedupe):
    label = "tomorrow" if hours == 24 else "in about 1 hour"
    return notify_patient(
        a, f"REMINDER_{hours}H", f"Reminder: your appointment is {label}",
        f"{_greeting(a)}\n\nThis is a reminder of your appointment {label}.\n\nDoctor: {_who(a)}\n"
        f"Hospital: {a.hospital.name}\nWhen: {_when(a)}\nToken: #{a.token_number}\n\n"
        f"Please arrive 10 minutes early and show your QR ticket at reception.\n\n- Qenova",
        f"Qenova reminder: appointment {label} - {_who(a)}, {_when(a)}, token #{a.token_number}.",
        dedupe=dedupe, sync=True,
    )