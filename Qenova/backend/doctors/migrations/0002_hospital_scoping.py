from django.db import migrations, models
import django.db.models.deletion


def backfill_hospital_data(apps, schema_editor):
    Hospital = apps.get_model("doctors", "Hospital")
    Department = apps.get_model("doctors", "Department")
    DoctorProfile = apps.get_model("doctors", "DoctorProfile")

    hospital, _ = Hospital.objects.get_or_create(
        registration_number="LEGACY-MEDIBOOK",
        defaults={
            "name": "Legacy MediBook Hospital",
            "address": "Update this hospital profile",
            "city": "Hyderabad",
            "state": "Telangana",
            "pincode": "000000",
            "phone": "0000000000",
            "email": "legacy@medibook.local",
            "description": "Automatically created to preserve existing local development data.",
            "status": "APPROVED",
        },
    )

    Department.objects.filter(hospital__isnull=True).update(hospital=hospital)
    for doctor in DoctorProfile.objects.filter(hospital__isnull=True).order_by("id"):
        doctor.hospital = hospital
        doctor.registration_number = f"LEGACY-DR-{doctor.id}"
        doctor.is_verified = True
        doctor.is_active = True
        doctor.save(update_fields=["hospital", "registration_number", "is_verified", "is_active"])


def reverse_backfill(apps, schema_editor):
    # The forward migration intentionally preserves existing local data.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0004_role_choices"),
        ("doctors", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Hospital",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=200)),
                ("registration_number", models.CharField(max_length=100, unique=True)),
                ("address", models.TextField()),
                ("city", models.CharField(max_length=100)),
                ("state", models.CharField(max_length=100)),
                ("pincode", models.CharField(max_length=10)),
                ("phone", models.CharField(max_length=20)),
                ("email", models.EmailField(max_length=254)),
                ("description", models.TextField(blank=True)),
                ("status", models.CharField(choices=[("PENDING", "Pending"), ("APPROVED", "Approved"), ("REJECTED", "Rejected")], default="PENDING", max_length=20)),
                ("rejection_reason", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("admin_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="managed_hospital", to="accounts.user")),
            ],
            options={"ordering": ["name"]},
        ),
        migrations.AddField(
            model_name="department",
            name="hospital",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="departments", to="doctors.hospital"),
        ),
        migrations.AlterField(
            model_name="department",
            name="name",
            field=models.CharField(max_length=100),
        ),
        migrations.AddField(
            model_name="doctorprofile",
            name="hospital",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name="doctors", to="doctors.hospital"),
        ),
        migrations.AddField(
            model_name="doctorprofile",
            name="registration_number",
            field=models.CharField(max_length=100, null=True, unique=True),
        ),
        migrations.AddField(
            model_name="doctorprofile",
            name="is_verified",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="doctorprofile",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name="doctorschedule",
            name="is_active",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(backfill_hospital_data, reverse_backfill),
        migrations.AlterField(
            model_name="doctorprofile",
            name="registration_number",
            field=models.CharField(max_length=100, unique=True),
        ),
        migrations.AlterField(
            model_name="department",
            name="hospital",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="departments", to="doctors.hospital"),
        ),
        migrations.AlterField(
            model_name="doctorprofile",
            name="hospital",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="doctors", to="doctors.hospital"),
        ),
        migrations.AddConstraint(
            model_name="department",
            constraint=models.UniqueConstraint(fields=("hospital", "name"), name="unique_hospital_department"),
        ),
    ]
