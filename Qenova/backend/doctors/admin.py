from django.contrib import admin
from .models import Hospital, Department, DoctorProfile, DoctorSchedule


@admin.register(Hospital)
class HospitalAdmin(admin.ModelAdmin):
    list_display = ("name", "registration_number", "city", "status", "admin_user", "created_at")
    list_filter = ("status", "city")
    search_fields = ("name", "registration_number", "email", "admin_user__email")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "hospital")
    list_filter = ("hospital",)
    search_fields = ("name", "hospital__name")


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ("doctor_name", "hospital", "department", "is_verified", "is_active")
    list_filter = ("hospital", "department", "is_verified", "is_active")
    search_fields = ("user__first_name", "user__last_name", "registration_number")

    @admin.display(description="Doctor name")
    def doctor_name(self, obj):
        return obj.user.get_full_name() or obj.user.username


@admin.register(DoctorSchedule)
class DoctorScheduleAdmin(admin.ModelAdmin):
    list_display = ("doctor", "weekday", "start_time", "end_time", "slot_minutes", "is_active")
    list_filter = ("weekday", "is_active")
