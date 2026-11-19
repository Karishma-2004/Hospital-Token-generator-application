from django.contrib.auth import authenticate
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User


class UserSerializer(serializers.ModelSerializer):
    hospital_name = serializers.SerializerMethodField()
    hospital_role = serializers.SerializerMethodField()
    effective_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id", "username", "email", "first_name", "last_name", "mobile",
            "role", "effective_role", "email_verified", "is_active", "hospital_name", "hospital_role",
        ]

    def get_effective_role(self, obj):
        return User.ROLE_ADMIN if obj.is_superuser else obj.role

    def get_hospital_name(self, obj):
        try:
            if obj.role == User.ROLE_RECEPTIONIST:
                staff = obj.hospital_staff
                return staff.hospital.name if staff.hospital.status == "APPROVED" else None
            if obj.role == User.ROLE_DOCTOR:
                return obj.doctor_profile.hospital.name
        except Exception:
            return None
        return None

    def get_hospital_role(self, obj):
        """HOSPITAL_ADMIN / RECEPTIONIST for hospital staff, otherwise None."""
        try:
            return obj.hospital_staff.staff_role if obj.role == User.ROLE_RECEPTIONIST else None
        except Exception:
            return None


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = [
            "username", "email", "password", "password_confirm",
            "first_name", "last_name", "mobile",
        ]

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value.lower()

    def validate(self, data):
        if data["password"] != data["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        return User.objects.create_user(
            is_active=False,
            email_verified=False,
            role=User.ROLE_USER,
            **validated_data,
        )


class LoginTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Informational claims for the frontend. The server never trusts these for
        # authorisation - every request re-checks role / hospital from the database.
        token["role"] = User.ROLE_ADMIN if user.is_superuser else user.role
        try:
            if user.role == User.ROLE_RECEPTIONIST:
                token["hospital_id"] = user.hospital_staff.hospital_id
                token["hospital_role"] = user.hospital_staff.staff_role
            elif user.role == User.ROLE_DOCTOR:
                token["hospital_id"] = user.doctor_profile.hospital_id
        except Exception:
            pass
        return token

    def validate(self, attrs):
        username = attrs.get("username")
        user = User.objects.filter(username=username).first()
        if user:
            if not user.is_active:
                raise serializers.ValidationError(
                    "This account is not active yet. Complete verification or wait for hospital approval."
                )
            if user.role == User.ROLE_USER and not user.email_verified:
                raise serializers.ValidationError("Please verify your email address before signing in.")
            if user.role == User.ROLE_RECEPTIONIST:
                try:
                    hospital = user.hospital_staff.hospital
                except Exception:
                    raise serializers.ValidationError("This staff account is not linked to a hospital. Contact the hospital admin.")
                if hospital.status != "APPROVED":
                    raise serializers.ValidationError("Hospital access is still awaiting Application Admin approval.")
            if user.role == User.ROLE_DOCTOR:
                try:
                    profile = user.doctor_profile
                except Exception:
                    raise serializers.ValidationError("Doctor profile is not configured. Contact the hospital staff.")
                if not profile.is_verified or not profile.is_active:
                    raise serializers.ValidationError("Your doctor account is not active. Contact the hospital staff.")
                if profile.hospital.status != "APPROVED":
                    raise serializers.ValidationError("Your hospital is not approved yet.")
        return super().validate(attrs)
