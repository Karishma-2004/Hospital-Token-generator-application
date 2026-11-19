from django.urls import path
from .views import NotificationView, ReportView, StatsView, UserDetailView, UserListView

from .settlements import PayoutView, SettlementListView
from .views import ReportView, StatsView, UserDetailView, UserListView

urlpatterns = [
    path("stats/", StatsView.as_view()),
    path("report/", ReportView.as_view()),
    path("users/", UserListView.as_view()),
    path("users/<int:pk>/", UserDetailView.as_view()),
    path("settlements/", SettlementListView.as_view()),
    path("payouts/", PayoutView.as_view()),
    path("notifications/", NotificationView.as_view()),
]