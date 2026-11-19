from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import (
    DepartmentViewSet, DoctorViewSet, ScheduleViewSet,
    HospitalRegistrationView, HospitalListView, HospitalDetailView,
    HospitalDoctorsView, HospitalDepartmentsView,
    ReceptionistDoctorCreateView, ReceptionistDoctorListView,
    ReceptionistDoctorVerifyView, ReceptionistDepartmentView,
    ReceptionistScheduleView, ReceptionistScheduleDetailView, ReceptionistDoctorDetailView,
    HospitalStaffView, ApplicationAdminHospitalView,
    ApplicationAdminHospitalDecisionView,
)

router = DefaultRouter()
router.register("departments", DepartmentViewSet, basename="department")
router.register("doctors", DoctorViewSet, basename="doctor")
router.register("schedules", ScheduleViewSet, basename="schedule")

urlpatterns = [
    path("hospitals/register/", HospitalRegistrationView.as_view()),
    path("hospitals/", HospitalListView.as_view()),
    path("hospitals/<int:hospital_id>/", HospitalDetailView.as_view()),
    path("hospitals/<int:hospital_id>/doctors/", HospitalDoctorsView.as_view()),
    path("hospitals/<int:hospital_id>/departments/", HospitalDepartmentsView.as_view()),
    path("receptionist/doctors/", ReceptionistDoctorListView.as_view()),
    path("receptionist/doctors/create/", ReceptionistDoctorCreateView.as_view()),
    path("receptionist/doctors/<int:doctor_id>/", ReceptionistDoctorDetailView.as_view()),
    path("receptionist/doctors/<int:doctor_id>/verify/", ReceptionistDoctorVerifyView.as_view()),
    path("receptionist/departments/", ReceptionistDepartmentView.as_view()),
    path("receptionist/schedules/", ReceptionistScheduleView.as_view()),
    path("receptionist/schedules/<int:schedule_id>/", ReceptionistScheduleDetailView.as_view()),
    path("hospital-admin/staff/", HospitalStaffView.as_view()),
    path("application-admin/hospitals/", ApplicationAdminHospitalView.as_view()),
    path("application-admin/hospitals/<int:hospital_id>/decision/", ApplicationAdminHospitalDecisionView.as_view()),
] + router.urls
