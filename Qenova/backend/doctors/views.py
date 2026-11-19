from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import filters, permissions, viewsets
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import User
from .access import (
    IsApplicationAdmin, IsHospitalAdmin, IsHospitalStaff,
    get_staff_hospital, is_application_admin,
)
from .admin_alerts import notify_admins_of_registration
from .models import Hospital, HospitalStaff, Department, DoctorProfile, DoctorSchedule
from .serializers import (
    HospitalSerializer, HospitalPublicSerializer, HospitalRegistrationSerializer, DepartmentSerializer,
    DoctorSerializer, DoctorStaffSerializer, DoctorCreateSerializer, DoctorUpdateSerializer,
    ScheduleSerializer, StaffCreateSerializer, StaffSerializer,
)


# --------------------------------------------------------------------------
# Public (no token): only APPROVED hospitals and their verified doctors
# --------------------------------------------------------------------------

class HospitalRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = HospitalRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            hospital = serializer.save()

        # Send email notification to the Application Admin
        notify_admins_of_registration(hospital)

        return Response({
            "message": (
                "Hospital registration submitted. Application Admin "
                "approval is required before the hospital can appear "
                "in the user portal."
            ),
            "hospital_id": hospital.id,
            "status": hospital.status,
        }, status=201)



class HospitalListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        qs = Hospital.objects.filter(status=Hospital.STATUS_APPROVED).order_by("name")
        q = request.query_params.get("search", "").strip()
        if q:
            qs = qs.filter(name__icontains=q)
        return Response(HospitalPublicSerializer(qs, many=True).data)


class HospitalDetailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, hospital_id):
        try:
            hospital = Hospital.objects.get(id=hospital_id, status=Hospital.STATUS_APPROVED)
        except Hospital.DoesNotExist:
            return Response({"detail": "Hospital not found."}, status=404)
        return Response(HospitalPublicSerializer(hospital).data)


class HospitalDoctorsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, hospital_id):
        try:
            hospital = Hospital.objects.get(id=hospital_id, status=Hospital.STATUS_APPROVED)
        except Hospital.DoesNotExist:
            return Response({"detail": "Hospital not found."}, status=404)
        doctors = DoctorProfile.objects.select_related("user", "department", "hospital").filter(
            hospital=hospital, is_active=True, is_verified=True
        )
        q = request.query_params.get("search", "").strip()
        department_id = request.query_params.get("department")
        if q:
            from django.db.models import Q
            doctors = doctors.filter(
                Q(user__first_name__icontains=q) | Q(user__last_name__icontains=q)
                | Q(specialization__icontains=q) | Q(department__name__icontains=q)
            )
        if department_id:
            doctors = doctors.filter(department_id=department_id)
        doctors = doctors.distinct().order_by("user__first_name", "user__last_name")
        return Response(DoctorSerializer(doctors, many=True).data)


class HospitalDepartmentsView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, hospital_id):
        departments = Department.objects.filter(
            hospital_id=hospital_id,
            hospital__status=Hospital.STATUS_APPROVED,
        ).order_by("name")
        return Response(DepartmentSerializer(departments, many=True).data)


# --------------------------------------------------------------------------
# Hospital staff (JWT + hospital admin / receptionist of an APPROVED hospital)
# --------------------------------------------------------------------------
class ReceptionistDoctorCreateView(APIView):
    permission_classes = [IsHospitalStaff]

    def post(self, request):
        serializer = DoctorCreateSerializer(data=request.data, context={"hospital": request.hospital})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            doctor = serializer.save()
        return Response({
            "message": "Doctor added. The doctor now appears to patients and can sign in.",
            "doctor": DoctorStaffSerializer(doctor).data,
        }, status=201)


class ReceptionistDoctorListView(APIView):
    permission_classes = [IsHospitalStaff]

    def get(self, request):
        doctors = DoctorProfile.objects.select_related("user", "department").prefetch_related("schedules").filter(
            hospital=request.hospital
        ).order_by("user__first_name")
        return Response(DoctorStaffSerializer(doctors, many=True).data)


class ReceptionistDoctorDetailView(APIView):
    """PATCH: edit fee / bio / department / active flag of a doctor in your hospital."""
    permission_classes = [IsHospitalStaff]

    def patch(self, request, doctor_id):
        try:
            doctor = DoctorProfile.objects.get(id=doctor_id, hospital=request.hospital)
        except DoctorProfile.DoesNotExist:
            return Response({"detail": "Doctor not found."}, status=404)
        serializer = DoctorUpdateSerializer(doctor, data=request.data, partial=True, context={"hospital": request.hospital})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DoctorStaffSerializer(doctor).data)


class ReceptionistDoctorVerifyView(APIView):
    """Kept for doctors created before auto-verification existed."""
    permission_classes = [IsHospitalStaff]

    def post(self, request, doctor_id):
        try:
            doctor = DoctorProfile.objects.select_related("user").get(id=doctor_id, hospital=request.hospital)
        except DoctorProfile.DoesNotExist:
            return Response({"detail": "Doctor not found."}, status=404)
        doctor.is_verified = True
        doctor.is_active = True
        doctor.user.is_active = True
        doctor.user.save(update_fields=["is_active"])
        doctor.save(update_fields=["is_verified", "is_active"])
        return Response({"message": "Doctor verified successfully."})


class ReceptionistDepartmentView(APIView):
    permission_classes = [IsHospitalStaff]

    def get(self, request):
        departments = Department.objects.filter(hospital=request.hospital).order_by("name")
        return Response(DepartmentSerializer(departments, many=True).data)

    def post(self, request):
        serializer = DepartmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        name = serializer.validated_data["name"].strip()
        if Department.objects.filter(hospital=request.hospital, name__iexact=name).exists():
            raise ValidationError({"name": "This department already exists."})
        department = Department.objects.create(
            hospital=request.hospital, name=name,
            description=serializer.validated_data.get("description", ""),
        )
        return Response(DepartmentSerializer(department).data, status=201)


class ReceptionistScheduleView(APIView):
    permission_classes = [IsHospitalStaff]

    def get(self, request):
        qs = DoctorSchedule.objects.filter(doctor__hospital=request.hospital)
        doctor_id = request.query_params.get("doctor")
        if doctor_id:
            qs = qs.filter(doctor_id=doctor_id)
        return Response(ScheduleSerializer(qs, many=True).data)

    def post(self, request):
        try:
            doctor = DoctorProfile.objects.get(id=request.data.get("doctor"), hospital=request.hospital)
        except (DoctorProfile.DoesNotExist, TypeError, ValueError):
            return Response({"detail": "Doctor not found in your hospital."}, status=404)
        serializer = ScheduleSerializer(data=request.data, context={"doctor": doctor})
        serializer.is_valid(raise_exception=True)
        schedule = serializer.save(doctor=doctor)
        return Response(ScheduleSerializer(schedule).data, status=201)


class ReceptionistScheduleDetailView(APIView):
    permission_classes = [IsHospitalStaff]

    def _get(self, request, schedule_id):
        return DoctorSchedule.objects.filter(id=schedule_id, doctor__hospital=request.hospital).first()

    def patch(self, request, schedule_id):
        schedule = self._get(request, schedule_id)
        if not schedule:
            return Response({"detail": "Schedule not found."}, status=404)
        serializer = ScheduleSerializer(schedule, data=request.data, partial=True, context={"doctor": schedule.doctor})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, schedule_id):
        schedule = self._get(request, schedule_id)
        if not schedule:
            return Response({"detail": "Schedule not found."}, status=404)
        schedule.delete()
        return Response(status=204)


class HospitalStaffView(APIView):
    """Hospital admin manages receptionists of their own hospital."""
    permission_classes = [IsHospitalAdmin]

    def get(self, request):
        staff = HospitalStaff.objects.select_related("user").filter(hospital=request.hospital).order_by("created_at")
        return Response(StaffSerializer(staff, many=True).data)

    def post(self, request):
        serializer = StaffCreateSerializer(data=request.data, context={"hospital": request.hospital})
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            membership = serializer.save()
        return Response(StaffSerializer(membership).data, status=201)


# --------------------------------------------------------------------------
# Application Admin (JWT + admin role): approve / reject hospitals
# --------------------------------------------------------------------------
class ApplicationAdminHospitalView(APIView):
    permission_classes = [IsApplicationAdmin]

    def get(self, request):
        status_filter = request.query_params.get("status")
        qs = Hospital.objects.select_related("admin_user").all()
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(HospitalSerializer(qs, many=True).data)


class ApplicationAdminHospitalDecisionView(APIView):
    permission_classes = [IsApplicationAdmin]

    def post(self, request, hospital_id):
        action = request.data.get("action")
        reason = str(request.data.get("reason", "")).strip()
        if action not in ["approve", "reject"]:
            return Response({"detail": "Action must be approve or reject."}, status=400)
        try:
            hospital = Hospital.objects.select_related("admin_user").get(id=hospital_id)
        except Hospital.DoesNotExist:
            return Response({"detail": "Hospital not found."}, status=404)

        with transaction.atomic():
            if action == "approve":
                hospital.status = Hospital.STATUS_APPROVED
                hospital.rejection_reason = ""
                hospital.save(update_fields=["status", "rejection_reason", "updated_at"])
                # Re-activate every staff login of this hospital (relevant if it was rejected before).
                User.objects.filter(hospital_staff__hospital=hospital).update(is_active=True, email_verified=True)
                subject = "Qenova hospital approved"
                body = f"Your hospital {hospital.name} has been approved. You can now sign in as the hospital admin and add doctors."
                result = {"message": "Hospital approved successfully."}
            else:
                hospital.status = Hospital.STATUS_REJECTED
                hospital.rejection_reason = reason or "Application was rejected by the Application Admin."
                hospital.save(update_fields=["status", "rejection_reason", "updated_at"])
                User.objects.filter(hospital_staff__hospital=hospital).update(is_active=False)
                subject = "Qenova hospital registration rejected"
                body = f"Your hospital {hospital.name} was not approved. Reason: {hospital.rejection_reason}"
                result = {"message": "Hospital rejected."}

        if hospital.admin_user:
            try:
                send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [hospital.admin_user.email], fail_silently=True)
            except Exception:
                pass
        return Response(result)


# --------------------------------------------------------------------------
# Router viewsets
# --------------------------------------------------------------------------
class DepartmentViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only for Application Admin (all hospitals) and hospital staff (own hospital).
    Writes go through /receptionist/departments/."""
    serializer_class = DepartmentSerializer

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_queryset(self):
        user = self.request.user
        if is_application_admin(user):
            return Department.objects.select_related("hospital").all()
        hospital = get_staff_hospital(user, approved_only=False)
        return Department.objects.filter(hospital=hospital) if hospital else Department.objects.none()


class DoctorViewSet(viewsets.ReadOnlyModelViewSet):
    """Public: verified doctors of approved hospitals. Staff/doctor/admin see more.
    Writes go through /receptionist/doctors/..."""
    serializer_class = DoctorSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]

    def get_serializer_class(self):
        user = self.request.user
        if user.is_authenticated and (is_application_admin(user) or user.role in (User.ROLE_RECEPTIONIST, User.ROLE_DOCTOR)):
            return DoctorStaffSerializer
        return DoctorSerializer

    search_fields = ["user__first_name", "user__last_name", "specialization", "department__name", "hospital__name"]
    ordering_fields = ["experience_years", "consultation_fee", "user__first_name"]
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = DoctorProfile.objects.select_related("user", "department", "hospital").prefetch_related("schedules")
        user = self.request.user
        public = qs.filter(is_active=True, is_verified=True, hospital__status=Hospital.STATUS_APPROVED)
        if not user.is_authenticated:
            return public
        if is_application_admin(user):
            return qs
        if user.role == User.ROLE_RECEPTIONIST:
            hospital = get_staff_hospital(user, approved_only=False)
            return qs.filter(hospital=hospital) if hospital else public
        if user.role == User.ROLE_DOCTOR:
            return qs.filter(user=user)
        return public


class ScheduleViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only. Writes go through /receptionist/schedules/."""
    serializer_class = ScheduleSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = DoctorSchedule.objects.select_related("doctor__hospital")
        user = self.request.user
        if is_application_admin(user):
            return qs
        if user.role == User.ROLE_RECEPTIONIST:
            hospital = get_staff_hospital(user, approved_only=False)
            return qs.filter(doctor__hospital=hospital) if hospital else qs.none()
        if user.role == User.ROLE_DOCTOR:
            return qs.filter(doctor__user=user)
        return qs.filter(
            doctor__is_active=True, doctor__is_verified=True,
            doctor__hospital__status=Hospital.STATUS_APPROVED,
        )
