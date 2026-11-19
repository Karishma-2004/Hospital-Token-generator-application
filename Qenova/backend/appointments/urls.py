from django.urls import path
from rest_framework.routers import DefaultRouter

from .queue_views import (
    DoctorCallNextView, DoctorCompleteView, DoctorQueueView, MyQueueView,
    QueueBoardView, ReceptionTodayView, ScanCheckInView, WalkInView,
)
from .extra_views import PayCashView, PayOrderView, PayVerifyView, PaymentConfigView, PrescriptionView
from .views import AppointmentViewSet, DoctorSlotsView

router = DefaultRouter()
router.register("", AppointmentViewSet, basename="appointment")

# These must stay ABOVE router.urls, otherwise "today/" would be read as an appointment id.
urlpatterns = [
    path("doctors/<int:doctor_id>/slots/", DoctorSlotsView.as_view(), name="doctor-slots"),

    # Sprint 5 - receptionist
    path("reception/today/", ReceptionTodayView.as_view()),
    path("reception/scan/", ScanCheckInView.as_view()),
    path("reception/walk-in/", WalkInView.as_view()),

    # Sprint 6 - doctor
    path("doctor/queue/", DoctorQueueView.as_view()),
    path("doctor/call-next/", DoctorCallNextView.as_view()),
    path("doctor/complete/", DoctorCompleteView.as_view()),

    # live queue
    path("queue-board/<int:hospital_id>/", QueueBoardView.as_view()),
    path("my-queue/", MyQueueView.as_view()),

    # Sprint 7 - payments and prescriptions
    path("payments/config/", PaymentConfigView.as_view()),
    path("<int:pk>/pay/", PayOrderView.as_view()),
    path("<int:pk>/pay/verify/", PayVerifyView.as_view()),
    path("<int:pk>/pay/cash/", PayCashView.as_view()),
    path("<int:pk>/prescription/", PrescriptionView.as_view()),
] + router.urls