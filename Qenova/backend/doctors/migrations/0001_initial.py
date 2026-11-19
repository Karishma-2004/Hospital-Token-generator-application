from django.db import migrations,models
import django.db.models.deletion
class Migration(migrations.Migration):
 dependencies=[('accounts','0001_initial')]
 operations=[
  migrations.CreateModel(name='Department',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('name',models.CharField(max_length=100,unique=True)),('description',models.TextField(blank=True))]),
  migrations.CreateModel(name='DoctorProfile',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('specialization',models.CharField(max_length=120)),('consultation_fee',models.DecimalField(decimal_places=2,default=0,max_digits=10)),('experience_years',models.PositiveIntegerField(default=0)),('bio',models.TextField(blank=True)),('department',models.ForeignKey(on_delete=django.db.models.deletion.PROTECT,related_name='doctors',to='doctors.department')),('user',models.OneToOneField(on_delete=django.db.models.deletion.CASCADE,related_name='doctor_profile',to='accounts.user'))]),
  migrations.CreateModel(name='DoctorSchedule',fields=[('id',models.BigAutoField(auto_created=True,primary_key=True,serialize=False,verbose_name='ID')),('weekday',models.PositiveSmallIntegerField(choices=[(0,'Monday'),(1,'Tuesday'),(2,'Wednesday'),(3,'Thursday'),(4,'Friday'),(5,'Saturday'),(6,'Sunday')])),('start_time',models.TimeField()),('end_time',models.TimeField()),('slot_minutes',models.PositiveIntegerField(default=15)),('doctor',models.ForeignKey(on_delete=django.db.models.deletion.CASCADE,related_name='schedules',to='doctors.doctorprofile'))]),
  migrations.AddConstraint(model_name='doctorschedule',constraint=models.UniqueConstraint(fields=('doctor','weekday','start_time','end_time'),name='doctors_doctor_schedule_unique')),
 ]
