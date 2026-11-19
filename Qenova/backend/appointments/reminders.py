"""24-hour and 1-hour appointment reminders (Sprint 7).

Run it with:  python manage.py send_reminders --loop        (keeps running, checks every minute)
          or: python manage.py send_reminders               (one pass, for Windows Task Scheduler / cron)
"""
from datetime import datetime, timedelta

from django.utils import timezone

from . import notify
from .models import Appointment


def run_reminders(now=None):
    now = now or timezone.now()
    today = timezone.localdate(now)
    appointments = (
        Appointment.objects.filter(
            status=Appointment.STATUS_BOOKED, patient__isnull=False,
            appointment_date__gte=today, appointment_date__lte=today + timedelta(days=2),
        )
        .select_related("patient", "doctor__user", "hospital")
    )
    sent = {"24h": 0, "1h": 0}
    for a in appointments:
        start = timezone.make_aware(datetime.combine(a.appointment_date, a.appointment_time))
        remaining = start - now
        if timedelta(0) < remaining <= timedelta(hours=1):
            hours = 1
        elif (
            timedelta(hours=1) < remaining <= timedelta(hours=24)
            and a.created_at <= start - timedelta(hours=24)   # skip the 24h reminder for last-minute bookings
        ):
            hours = 24
        else:
            continue
        key = f"REMINDER_{hours}H:{a.id}:{a.appointment_date.isoformat()}:{a.appointment_time.strftime('%H%M')}"
        if notify.reminder(a, hours, key):
            sent[f"{hours}h"] += 1
    return sent
