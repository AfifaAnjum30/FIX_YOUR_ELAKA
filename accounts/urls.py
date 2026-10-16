from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "accounts"  # enables {% url 'accounts:login' %}

urlpatterns = [
    # Registration
    path("register/", views.CitizenRegisterView.as_view(), name="register"),
    path("register/authority/", views.AuthorityRegisterView.as_view(), name="authority_register"),

    # Auth
    path("login/", views.UserLoginView.as_view(), name="login"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("password-change/", views.UserPasswordChangeView.as_view(), name="password_change"),

    # Dashboards
    path("dashboard/", views.DashboardRedirectView.as_view(), name="dashboard"),
    path("dashboard/citizen/", views.CitizenDashboardView.as_view(), name="citizen_dashboard"),
    path("dashboard/authority/", views.AuthorityDashboardView.as_view(), name="authority_dashboard"),
    path("authority/pending/", views.PendingApprovalView.as_view(), name="pending_approval"),
    path("profile/", views.ProfileView.as_view(), name="profile"),

    # Admin approval workflow
    path("manage/authorities/", views.PendingAuthorityListView.as_view(), name="admin_pending_authorities"),
    path("manage/authorities/<int:pk>/approve/", views.AuthorityApproveView.as_view(), name="authority_approve"),
    path("manage/authorities/<int:pk>/reject/", views.AuthorityRejectView.as_view(), name="authority_reject"),
]