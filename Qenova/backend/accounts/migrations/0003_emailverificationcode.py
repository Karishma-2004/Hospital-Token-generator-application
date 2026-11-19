from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies=[('accounts','0002_user_email_verified')]
    operations=[migrations.CreateModel(name='EmailVerificationCode',fields=[
        ('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),
        ('code',models.CharField(max_length=6)),
        ('created_at',models.DateTimeField(auto_now_add=True)),
        ('expires_at',models.DateTimeField()),
        ('used',models.BooleanField(default=False)),
        ('user',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='verification_codes',to='accounts.user')),
    ],options={'ordering':['-created_at']})]
