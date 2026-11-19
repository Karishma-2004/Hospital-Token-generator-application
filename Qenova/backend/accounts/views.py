import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import EmailVerificationCode, User
from .serializers import UserSerializer, RegisterSerializer

UserModel = get_user_model()


def frontend_url(path):
    return f"{getattr(settings, 'FRONTEND_URL', 'http://localhost:5173').rstrip('/')}/{path.lstrip('/')}"


def create_verification_code(user):
    EmailVerificationCode.objects.filter(user=user, used=False).update(used=True)
    code = f"{secrets.randbelow(1000000):06d}"
    obj = EmailVerificationCode.objects.create(
        user=user,
        code=code,
        expires_at=timezone.now() + timedelta(minutes=10),
    )
    send_mail(
        "Qenova email verification code",
        f"Hello {user.first_name or user.username},\n\nYour Qenova verification code is: {code}\n\nThis code expires in 10 minutes.",
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    return obj


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @transaction.atomic
    def perform_create(self, serializer):
        user = serializer.save()
        try:
            create_verification_code(user)
        except Exception:
            user.delete()
            raise


class VerifyEmailCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        code = str(request.data.get("code", "")).strip()
        if not email or len(code) != 6 or not code.isdigit():
            return Response({"detail": "Enter the 6-digit verification code."}, status=400)
        user = UserModel.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"detail": "Invalid verification code."}, status=400)
        if user.email_verified:
            return Response({"detail": "Email is already verified. You can sign in."})
        verification = user.verification_codes.filter(used=False).first()
        if not verification:
            return Response({"detail": "No active verification code. Request a new code."}, status=400)
        if verification.expires_at < timezone.now():
            return Response({"detail": "This verification code has expired. Request a new code."}, status=400)
        if verification.code != code:
            return Response({"detail": "Incorrect verification code."}, status=400)
        verification.used = True
        verification.save(update_fields=["used"])
        user.email_verified = True
        user.is_active = True
        user.save(update_fields=["email_verified", "is_active"])
        return Response({"detail": "Email verified successfully. You can now sign in."})


class ResendVerificationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        user = UserModel.objects.filter(email__iexact=email).first()
        if not user:
            return Response({"detail": "No account was found with that email address."}, status=404)
        if user.email_verified:
            return Response({"detail": "Email is already verified. You can sign in."})
        try:
            create_verification_code(user)
        except Exception as exc:
            return Response({"detail": f"Email could not be sent. Check backend/.env Gmail settings. Error: {exc}"}, status=500)
        return Response({"detail": "A new 6-digit verification code has been sent to your email."})


class PasswordResetRequestView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email", "").strip().lower()
        user = UserModel.objects.filter(email__iexact=email).first()
        if user and user.email_verified:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            link = frontend_url(f"reset-password/{uid}/{token}")
            send_mail(
                "Reset your Qenova password",
                f"Hello {user.first_name or user.username},\n\nReset your password using this link:\n{link}\n\nIf you did not request this, you can ignore this email.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        return Response({"detail": "If an account with that email exists, a password reset link has been sent."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, uid, token):
        password = request.data.get("password", "")
        confirm = request.data.get("password_confirm", "")
        if len(password) < 8:
            return Response({"detail": "Password must be at least 8 characters."}, status=400)
        if password != confirm:
            return Response({"detail": "Passwords do not match."}, status=400)
        try:
            user = UserModel.objects.get(pk=force_str(urlsafe_base64_decode(uid)))
        except (TypeError, ValueError, OverflowError, UserModel.DoesNotExist):
            return Response({"detail": "Invalid reset link."}, status=400)
        if not default_token_generator.check_token(user, token):
            return Response({"detail": "This reset link is invalid or expired."}, status=400)
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"detail": "Password reset successfully. You can now sign in."})


class VerifyEmailView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, uid, token):
        return Response({"detail": "Use the 6-digit verification code sent to your email."}, status=410)


class MeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)
