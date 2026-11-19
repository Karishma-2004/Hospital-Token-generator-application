from django.db import migrations, models


def convert_patient_role(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    User.objects.filter(role="PATIENT").update(role="USER")


class Migration(migrations.Migration):
    dependencies = [("accounts", "0003_emailverificationcode")]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="role",
            field=models.CharField(
                choices=[
                    ("USER", "User"),
                    ("DOCTOR", "Doctor"),
                    ("RECEPTIONIST", "Receptionist"),
                    ("ADMIN", "Application Admin"),
                ],
                default="USER",
                max_length=20,
            ),
        ),
        migrations.RunPython(convert_patient_role, migrations.RunPython.noop),
    ]
