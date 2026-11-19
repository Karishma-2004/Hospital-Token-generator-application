from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .serializers import LoginTokenObtainPairSerializer


class LoginRateThrottle(AnonRateThrottle):
    """Limits sign-in attempts per IP address (rate set by LOGIN_RATE_LIMIT, default 30/min)."""
    scope = "login"


class LoginTokenView(TokenObtainPairView):
    serializer_class = LoginTokenObtainPairSerializer
    throttle_classes = [LoginRateThrottle]


class LogoutView(APIView):
    """Blacklists the refresh token so it can no longer be used after logout."""
    permission_classes = [permissions.AllowAny]
    authentication_classes = []

    def post(self, request):
        refresh = request.data.get("refresh")
        if refresh:
            try:
                RefreshToken(refresh).blacklist()
            except TokenError:
                pass  # already expired / blacklisted - logout is still successful
        return Response(status=status.HTTP_205_RESET_CONTENT)
