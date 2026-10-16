from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, FormView, ListView, RedirectView, TemplateView

from .forms import (
    AuthorityRegistrationForm,
    CitizenRegistrationForm,
    LoginForm,
    StyledPasswordChangeForm,
)
from .mixins import (
    AdminRequiredMixin,
    AnonymousOnlyMixin,
    ApprovedAuthorityRequiredMixin,
    AuthorityRequiredMixin,
    CitizenRequiredMixin,
)
from .models import AuthorityProfile


# ------------------------------------------------------------ Registration
class CitizenRegisterView(AnonymousOnlyMixin, CreateView):
    form_class = CitizenRegistrationForm
    template_name = "accounts/register.html"

    def form_valid(self, form):
        user = form.save()
        login(self.request, user)  # log in right after sign-up
        messages.success(self.request, "Welcome to FixIt Local! Your account has been created.")
        return redirect("accounts:dashboard")


class AuthorityRegisterView(AnonymousOnlyMixin, FormView):
    form_class = AuthorityRegistrationForm
    template_name = "accounts/authority_register.html"

    def form_valid(self, form):
        user = form.save()  # creates User + AuthorityProfile(pending)
        login(self.request, user)
        messages.info(
            self.request,
            "Application submitted. An administrator must approve your account "
            "before you can access authority features.",
        )
        return redirect("accounts:pending_approval")


# ------------------------------------------------------------ Login / logout / password
class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def get_default_redirect_url(self):
        # Used when there is no ?next= parameter: route by role.
        return reverse("accounts:dashboard")

    def form_valid(self, form):
        user = form.get_user()
        messages.success(self.request, f"Welcome back, {user.first_name or user.username}!")
        return super().form_valid(form)


class UserPasswordChangeView(LoginRequiredMixin, SuccessMessageMixin, PasswordChangeView):
    form_class = StyledPasswordChangeForm
    template_name = "accounts/password_change.html"
    success_url = reverse_lazy("accounts:profile")
    success_message = "Your password was changed successfully."


# Logout uses django.contrib.auth.views.LogoutView directly in urls.py
# (Django 5+ requires logout via POST, which the navbar form does).


# ------------------------------------------------------------ Dashboards
class DashboardRedirectView(LoginRequiredMixin, RedirectView):
    """Single 'Dashboard' link that sends each role to the right place."""

    def get_redirect_url(self, *args, **kwargs):
        user = self.request.user
        if user.is_platform_admin:
            return reverse("accounts:admin_pending_authorities")
        if user.is_authority:
            return reverse("accounts:authority_dashboard")
        return reverse("accounts:citizen_dashboard")


class CitizenDashboardView(CitizenRequiredMixin, TemplateView):
    template_name = "accounts/citizen_dashboard.html"


class AuthorityDashboardView(ApprovedAuthorityRequiredMixin, TemplateView):
    template_name = "accounts/authority_dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = self.request.user.authority_profile
        return context


class PendingApprovalView(AuthorityRequiredMixin, TemplateView):
    """Shown to authorities whose account is pending or rejected."""

    template_name = "accounts/pending_approval.html"

    def dispatch(self, request, *args, **kwargs):
        # Already approved? Skip this page.
        if request.user.is_authenticated and request.user.is_approved_authority:
            return redirect("accounts:authority_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = self.request.user.authority_profile_or_none
        return context


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["profile"] = self.request.user.authority_profile_or_none
        return context


# ------------------------------------------------------------ Admin: authority approval
class PendingAuthorityListView(AdminRequiredMixin, ListView):
    template_name = "accounts/pending_authorities.html"
    context_object_name = "applications"

    def get_queryset(self):
        return (
            AuthorityProfile.objects.filter(
                approval_status=AuthorityProfile.ApprovalStatus.PENDING
            )
            .select_related("user")
            .order_by("user__date_joined")
        )


class AuthorityApproveView(AdminRequiredMixin, View):
    http_method_names = ["post"]  # state changes must never happen on GET

    def post(self, request, pk):
        profile = get_object_or_404(AuthorityProfile.objects.select_related("user"), pk=pk)
        profile.approve(request.user)
        messages.success(request, f"{profile.user} has been approved.")
        return redirect("accounts:admin_pending_authorities")


class AuthorityRejectView(AdminRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        profile = get_object_or_404(AuthorityProfile.objects.select_related("user"), pk=pk)
        reason = request.POST.get("reason", "").strip()
        if not reason:
            messages.error(request, "Please provide a rejection reason.")
        else:
            profile.reject(request.user, reason)
            messages.warning(request, f"{profile.user} has been rejected.")
        return redirect("accounts:admin_pending_authorities")