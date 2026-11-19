from django.urls import path
from .token_views import LogoutView
from .views import RegisterView,MeView,VerifyEmailView,VerifyEmailCodeView,ResendVerificationView,PasswordResetRequestView,PasswordResetConfirmView
urlpatterns=[
    path('register/',RegisterView.as_view()),
    path('verify-email/',VerifyEmailCodeView.as_view()),
    path('verify-email/<uid>/<token>/',VerifyEmailView.as_view()),
    path('resend-verification/',ResendVerificationView.as_view()),
    path('password-reset/',PasswordResetRequestView.as_view()),
    path('password-reset/<uid>/<token>/',PasswordResetConfirmView.as_view()),
    path('me/',MeView.as_view()),
    path('logout/',LogoutView.as_view()),
]
