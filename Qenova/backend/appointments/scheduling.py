from datetime import datetime, timedelta

from django.utils import timezone

MAX_DAYS_AHEAD = 60


def active_schedules(doctor, day):
    return [s for s in doctor.schedules.all() if s.is_active and s.weekday == day.weekday()]


def find_schedule(doctor, day, tm):
    """Return the session (a doctor can have several per day) whose slot grid contains `tm`."""
    for s in active_schedules(doctor, day):
        if not (s.start_time <= tm < s.end_time):
            continue
        offset = (tm.hour * 60 + tm.minute) - (s.start_time.hour * 60 + s.start_time.minute)
        if offset % s.slot_minutes == 0:
            return s
    return None


def slot_datetime(day, tm):
    return timezone.make_aware(datetime.combine(day, tm))


def is_past(day, tm):
    return slot_datetime(day, tm) <= timezone.now()


def slot_end(day, tm, schedule):
    return (datetime.combine(day, tm) + timedelta(minutes=schedule.slot_minutes)).time()
