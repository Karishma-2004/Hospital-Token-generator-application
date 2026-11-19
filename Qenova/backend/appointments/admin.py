from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ("id", "hospital", "doctor", "patient", "appointment_date", "appointment_time", "token_number", "status")
    list_filter = ("hospital", "status", "appointment_date")
    search_fields = ("patient__username", "patient__email", "doctor__user__first_name", "doctor__user__last_name", "hospital__name")
