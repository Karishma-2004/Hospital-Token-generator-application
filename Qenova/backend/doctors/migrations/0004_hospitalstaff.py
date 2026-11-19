from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def backfill_staff(apps, schema_editor):
    Hospital = apps.get_model("doctors", "Hospital")
    HospitalStaff = apps.get_model("doctors", "HospitalStaff")
    for hospital in Hospital.objects.exclude(admin_user__isnull=True):
        HospitalStaff.objects.get_or_create(
            user_id=hospital.admin_user_id,
            defaults={"hospital_id": hospital.id, "staff_role": "HOSPITAL_ADMIN"},
        )


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("doctors", "0003_alter_department_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="HospitalStaff",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("staff_role", models.CharField(choices=[("HOSPITAL_ADMIN", "Hospital admin"), ("RECEPTIONIST", "Receptionist")], default="RECEPTIONIST", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("hospital", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="staff", to="doctors.hospital")),
                ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="hospital_staff", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.RunPython(backfill_staff, migrations.RunPython.noop),
    ]
