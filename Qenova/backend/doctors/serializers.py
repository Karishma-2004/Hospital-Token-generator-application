from django.contrib.auth import get_user_model
from django.db import transaction

from rest_framework import serializers

from .models import (
    Hospital,
    HospitalStaff,
    Department,
    DoctorProfile,
    DoctorSchedule,
)


User = get_user_model()


# ============================================================
# HOSPITAL
# ============================================================

class HospitalSerializer(serializers.ModelSerializer):
    admin_name = serializers.SerializerMethodField()
    admin_email = serializers.SerializerMethodField()

    class Meta:
        model = Hospital

        fields = [
            "id",
            "name",
            "registration_number",
            "address",
            "city",
            "state",
            "pincode",
            "phone",
            "email",
            "description",
            "status",
            "rejection_reason",
            "admin_name",
            "admin_email",
            "created_at",
        ]

    def get_admin_name(self, obj):
        if obj.admin_user:
            return obj.admin_user.get_full_name()

        return ""

    def get_admin_email(self, obj):
        if obj.admin_user:
            return obj.admin_user.email

        return ""


class HospitalPublicSerializer(serializers.ModelSerializer):
    """
    Information visible to patients/users.

    Only approved hospitals should be passed to this serializer
    by the corresponding view.
    """

    class Meta:
        model = Hospital

        fields = [
            "id",
            "name",
            "address",
            "city",
            "state",
            "pincode",
            "phone",
            "email",
            "description",
        ]


# ============================================================
# HOSPITAL REGISTRATION
# ============================================================

class HospitalRegistrationSerializer(serializers.Serializer):
    name = serializers.CharField(
        max_length=200,
    )

    registration_number = serializers.CharField(
        max_length=100,
    )

    address = serializers.CharField()

    city = serializers.CharField(
        max_length=100,
    )

    state = serializers.CharField(
        max_length=100,
    )

    pincode = serializers.CharField(
        max_length=10,
    )

    phone = serializers.CharField(
        max_length=20,
    )

    email = serializers.EmailField()

    description = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    admin_name = serializers.CharField(
        max_length=150,
    )

    admin_email = serializers.EmailField()

    admin_password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    def validate_registration_number(self, value):
        if Hospital.objects.filter(
            registration_number=value
        ).exists():
            raise serializers.ValidationError(
                "A hospital with this registration number already exists."
            )

        return value

    def validate_admin_email(self, value):
        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value.lower()

    @transaction.atomic
    def create(self, validated_data):
        admin_name = validated_data.pop("admin_name")
        admin_email = validated_data.pop("admin_email")
        admin_password = validated_data.pop("admin_password")

        name_parts = admin_name.strip().split(" ", 1)

        first_name = name_parts[0]

        last_name = (
            name_parts[1]
            if len(name_parts) > 1
            else ""
        )

        # Create receptionist/hospital account.
        user = User.objects.create_user(
            username=admin_email,
            email=admin_email,
            password=admin_password,
            first_name=first_name,
            last_name=last_name,
            role=User.ROLE_RECEPTIONIST,
            is_active=False,
            email_verified=True,
        )

        # Hospital starts as PENDING.
        hospital = Hospital.objects.create(
            **validated_data,
            admin_user=user,
            status=Hospital.STATUS_PENDING,
        )

        # Link receptionist account to hospital.
        HospitalStaff.objects.create(
            user=user,
            hospital=hospital,
            staff_role=HospitalStaff.ROLE_ADMIN,
        )

        return hospital


# ============================================================
# DEPARTMENT
# ============================================================

class DepartmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = Department

        fields = [
            "id",
            "hospital",
            "name",
            "description",
        ]

        read_only_fields = [
            "hospital",
        ]


# ============================================================
# DOCTOR SCHEDULE
# ============================================================

class ScheduleSerializer(serializers.ModelSerializer):

    class Meta:
        model = DoctorSchedule

        fields = [
            "id",
            "doctor",
            "weekday",
            "start_time",
            "end_time",
            "slot_minutes",
            "is_active",
        ]

        read_only_fields = [
            "doctor",
        ]

    def validate(self, data):
        start = data.get(
            "start_time",
            getattr(
                self.instance,
                "start_time",
                None,
            ),
        )

        end = data.get(
            "end_time",
            getattr(
                self.instance,
                "end_time",
                None,
            ),
        )

        minutes = data.get(
            "slot_minutes",
            getattr(
                self.instance,
                "slot_minutes",
                15,
            ),
        )

        weekday = data.get(
            "weekday",
            getattr(
                self.instance,
                "weekday",
                None,
            ),
        )

        # Validate time range.
        if start and end and end <= start:
            raise serializers.ValidationError(
                {
                    "end_time": (
                        "End time must be after start time."
                    )
                }
            )

        # Validate slot length.
        if minutes is not None and not (
            5 <= minutes <= 120
        ):
            raise serializers.ValidationError(
                {
                    "slot_minutes": (
                        "Slot length must be between "
                        "5 and 120 minutes."
                    )
                }
            )

        doctor = (
            self.context.get("doctor")
            or getattr(
                self.instance,
                "doctor",
                None,
            )
        )

        # Prevent overlapping schedules.
        if (
            doctor
            and start
            and end
            and weekday is not None
        ):
            clash = DoctorSchedule.objects.filter(
                doctor=doctor,
                weekday=weekday,
                is_active=True,
                start_time__lt=end,
                end_time__gt=start,
            )

            if self.instance:
                clash = clash.exclude(
                    pk=self.instance.pk
                )

            if clash.exists():
                raise serializers.ValidationError(
                    "This session overlaps another session on the same day."
                )

        return data


# ============================================================
# DOCTOR
# ============================================================

class DoctorSerializer(serializers.ModelSerializer):
    """
    Public/patient doctor serializer.

    IMPORTANT:
    Doctor email and mobile are NOT returned here.
    """

    user = serializers.SerializerMethodField()

    department_name = serializers.CharField(
        source="department.name",
        read_only=True,
    )

    hospital_name = serializers.CharField(
        source="hospital.name",
        read_only=True,
    )

    schedules = ScheduleSerializer(
        many=True,
        read_only=True,
    )

    class Meta:
        model = DoctorProfile

        fields = [
            "id",
            "user",
            "hospital",
            "hospital_name",
            "department",
            "department_name",
            "specialization",
            "consultation_fee",
            "experience_years",
            "bio",
            "registration_number",
            "is_verified",
            "is_active",
            "schedules",
        ]

    def get_user(self, obj):
        return {
            "id": obj.user.id,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
        }


class DoctorStaffSerializer(DoctorSerializer):
    """
    Serializer used by hospital/receptionist staff.

    Staff can see doctor login email and mobile.
    """

    def get_user(self, obj):
        data = super().get_user(obj)

        data.update(
            {
                "email": obj.user.email,
                "mobile": obj.user.mobile,
            }
        )

        return data


# ============================================================
# CREATE DOCTOR
# ============================================================

class DoctorCreateSerializer(serializers.Serializer):
    """
    Receptionist creates a doctor account.

    Doctor authentication is managed by the receptionist.

    Email/mobile/password are stored on User.
    Professional information is stored on DoctorProfile.
    """

    first_name = serializers.CharField(
        max_length=150,
    )

    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )

    email = serializers.EmailField()

    mobile = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.all(),
    )

    specialization = serializers.CharField(
        max_length=120,
    )

    consultation_fee = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
    )

    experience_years = serializers.IntegerField(
        min_value=0,
        default=0,
    )

    bio = serializers.CharField(
        required=False,
        allow_blank=True,
    )

    registration_number = serializers.CharField(
        max_length=100,
    )

    def validate_email(self, value):
        """
        Doctor email must be unique.
        """

        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value.lower()

    def validate_registration_number(self, value):
        """
        Doctor professional registration number
        must be unique.
        """

        if DoctorProfile.objects.filter(
            registration_number=value
        ).exists():
            raise serializers.ValidationError(
                "A doctor with this registration number already exists."
            )

        return value

    def validate_department(self, value):
        """
        Prevent receptionist from assigning a doctor
        to a department belonging to another hospital.
        """

        hospital = self.context["hospital"]

        if value.hospital_id != hospital.id:
            raise serializers.ValidationError(
                "Select a department belonging to your hospital."
            )

        return value

    def validate_password(self, value):
        """
        Run Django's password validators.
        """

        from django.contrib.auth.password_validation import (
            validate_password,
        )

        validate_password(value)

        return value

    @transaction.atomic
    def create(self, validated_data):
        """
        Create:

            1. User account
            2. DoctorProfile

        Everything is inside one database transaction.
        """

        password = validated_data.pop(
            "password"
        )

        department = validated_data.pop(
            "department"
        )

        hospital = self.context["hospital"]

        # Take account information out of validated_data.
        email = validated_data.pop("email")

        first_name = validated_data.pop(
            "first_name"
        )

        last_name = validated_data.pop(
            "last_name",
            "",
        )

        mobile = validated_data.pop(
            "mobile",
            "",
        )

        # ----------------------------------------------------
        # CREATE USER
        # ----------------------------------------------------

        user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            mobile=mobile,
            role=User.ROLE_DOCTOR,
            is_active=True,
            email_verified=True,
        )

        # ----------------------------------------------------
        # CREATE DOCTOR PROFILE
        # ----------------------------------------------------

        doctor = DoctorProfile.objects.create(
            user=user,
            hospital=hospital,
            department=department,
            is_verified=True,
            is_active=True,
            **validated_data,
        )

        return doctor


# ============================================================
# UPDATE DOCTOR
# ============================================================

class DoctorUpdateSerializer(serializers.ModelSerializer):
    """
    Hospital staff can update professional information
    for a doctor belonging to their hospital.
    """

    class Meta:
        model = DoctorProfile

        fields = [
            "department",
            "specialization",
            "consultation_fee",
            "experience_years",
            "bio",
            "is_active",
        ]

    def validate_department(self, value):
        hospital = self.context["hospital"]

        if value.hospital_id != hospital.id:
            raise serializers.ValidationError(
                "Select a department belonging to your hospital."
            )

        return value


# ============================================================
# CREATE RECEPTIONIST / STAFF
# ============================================================

class StaffCreateSerializer(serializers.Serializer):
    """
    Hospital staff account creation.

    The user account is always created with
    User.role == RECEPTIONIST.
    """

    first_name = serializers.CharField(
        max_length=150,
    )

    last_name = serializers.CharField(
        max_length=150,
        required=False,
        allow_blank=True,
    )

    email = serializers.EmailField()

    mobile = serializers.CharField(
        max_length=20,
        required=False,
        allow_blank=True,
    )

    password = serializers.CharField(
        write_only=True,
        min_length=8,
    )

    def validate_email(self, value):
        if User.objects.filter(
            email__iexact=value
        ).exists():
            raise serializers.ValidationError(
                "An account with this email already exists."
            )

        return value.lower()

    def validate_password(self, value):
        from django.contrib.auth.password_validation import (
            validate_password,
        )

        validate_password(value)

        return value

    @transaction.atomic
    def create(self, validated_data):
        hospital = self.context["hospital"]

        user = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data.get(
                "last_name",
                "",
            ),
            mobile=validated_data.get(
                "mobile",
                "",
            ),
            role=User.ROLE_RECEPTIONIST,
            is_active=True,
            email_verified=True,
        )

        return HospitalStaff.objects.create(
            user=user,
            hospital=hospital,
            staff_role=HospitalStaff.ROLE_RECEPTIONIST,
        )


# ============================================================
# STAFF RESPONSE
# ============================================================

class StaffSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        source="user.first_name"
    )

    last_name = serializers.CharField(
        source="user.last_name"
    )

    email = serializers.CharField(
        source="user.email"
    )

    mobile = serializers.CharField(
        source="user.mobile"
    )

    is_active = serializers.BooleanField(
        source="user.is_active"
    )

    class Meta:
        model = HospitalStaff

        fields = [
            "id",
            "first_name",
            "last_name",
            "email",
            "mobile",
            "staff_role",
            "is_active",
        ]