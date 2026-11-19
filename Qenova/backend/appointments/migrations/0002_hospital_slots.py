from datetime import datetime, timedelta
from django.db import migrations, models
import django.db.models.deletion
from django.db.models import Q


def backfill_appointment_data(apps, schema_editor):
    Appointment = apps.get_model("appointments", "Appointment")
    DoctorProfile = apps.get_model("doctors", "DoctorProfile")
    for appointment in Appointment.objects.select_related("doctor__hospital").all():
        appointment.hospital_id = appointment.doctor.hospital_id
        appointment.end_time = (datetime.combine(appointment.appointment_date, appointment.appointment_time) + timedelta(minutes=15)).time()
        appointment.save(update_fields=["hospital", "end_time"])


class Migration(migrations.Migration):
    dependencies = [
        ("doctors", "0002_hospital_scoping"),
        ("appointments", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="appointment",
            name="hospital",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="doctors.hospital"),
        ),
        migrations.AddField(
            model_name="appointment",
            name="end_time",
            field=models.TimeField(null=True),
        ),
        migrations.AddField(
            model_name="appointment",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="status",
            field=models.CharField(choices=[("BOOKED", "Booked"), ("CHECKED_IN", "Checked In"), ("COMPLETED", "Completed"), ("CANCELLED", "Cancelled")], default="BOOKED", max_length=20),
        ),
        migrations.RunPython(backfill_appointment_data, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="appointment",
            name="hospital",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="appointments", to="doctors.hospital"),
        ),
        migrations.AlterField(
            model_name="appointment",
            name="end_time",
            field=models.TimeField(),
        ),
        migrations.RemoveConstraint(
            model_name="appointment",
            name="unique_doctor_day_token",
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.UniqueConstraint(condition=Q(status__in=["BOOKED", "CHECKED_IN"]), fields=("doctor", "appointment_date", "appointment_time"), name="unique_active_doctor_slot"),
        ),
        migrations.AddConstraint(
            model_name="appointment",
            constraint=models.UniqueConstraint(fields=("hospital", "appointment_date", "token_number"), name="unique_hospital_day_token"),
        ),
    ]
