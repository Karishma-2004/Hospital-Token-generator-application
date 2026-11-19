from django.contrib import admin
from django.urls import include, path
from rest_framework_simplejwt.views import TokenRefreshView

from accounts.token_views import LoginTokenView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/token/", LoginTokenView.as_view(), name="token"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/auth/", include("accounts.urls")),
    path("api/doctors/", include("doctors.urls")),
    path("api/appointments/", include("appointments.urls")),
    path("api/admin-panel/", include("adminpanel.urls")),
]
