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
    reports_shown = 6      # recent reports on the dashboard ("View all" lists the rest)
    activity_shown = 6

    # Note shown under the tracker; describes the current state only (no dates invented).
    PROGRESS_NOTES = {
        "pending": "Waiting for an authority to review this report.",
        "reported": "Verified. Waiting for work to begin.",
        "in_progress": "Work on this issue is under way.",
        "problem_fixed": "The fix is done and awaiting final resolution.",
    }

    @classmethod
    def _progress(cls, report):
        """
        Build the progress tracker from the report's real status fields.
        Steps follow the backend workflow: Submitted -> Verified -> then the
        report's own operational steps (physical reports include 'Problem Fixed',
        safety reports end at 'Closed'). There is no 'Assigned' status in the
        backend, so none is shown.
        """
        from reports.models import Report

        labels = dict(Report.OPERATIONAL_STATUS)

        if report.verification_status == "rejected":
            verification = getattr(report, "verification", None)
            return {
                "steps": [
                    {"label": "Submitted", "state": "done"},
                    {"label": "Rejected", "state": "rejected"},
                ],
                "note": "This report was rejected by the authority.",
                "remarks": (verification.remarks if verification else ""),
            }

        stages = list(report.workflow_steps)  # e.g. reported, in_progress, ..., resolved
        if report.operational_status not in stages:
            stages.append(report.operational_status)  # e.g. admin-set 'closed'
        steps = [("Submitted", "submitted"), ("Verified", "verified")]
        steps += [(labels[s], s) for s in stages[1:]]

        if report.verification_status == "pending":
            reached, note_key = 0, "pending"
        else:
            reached = 1 + stages.index(report.operational_status)
            note_key = report.operational_status

        finished = report.operational_status in (Report.RESOLVED, Report.CLOSED) and (
            report.verification_status == "verified"
        )
        built = []
        for i, (label, _key) in enumerate(steps):
            if finished or i < reached:
                state = "done"
            elif i == reached:
                state = "current"
            else:
                state = "todo"
            built.append({"label": label, "state": state})

        return {"steps": built, "note": "" if finished else cls.PROGRESS_NOTES.get(note_key, "")}

    def _activity(self, user):
        """
        Recent activity built from real records only: report submissions,
        verification decisions and status changes. (There is no notification
        model in the project, so nothing here is a push notification.)
        """
        from reports.models import Report, ReportStatusHistory, Verification

        n = self.activity_shown
        events = []

        for r in Report.objects.filter(reporter=user).order_by("-created_at")[:n]:
            events.append({
                "when": r.created_at, "report": r, "icon": "bi-send-check", "tone": "teal",
                "prefix": "You submitted ", "suffix": "",
            })

        decisions = {
            "verified": ("bi-patch-check-fill", "sage", " was verified"),
            "rejected": ("bi-x-circle-fill", "danger", " was rejected"),
        }
        for v in (
            Verification.objects.filter(report__reporter=user, status__in=decisions)
            .select_related("report")
            .order_by("-verified_at")[:n]
        ):
            icon, tone, suffix = decisions[v.status]
            events.append({
                "when": v.verified_at, "report": v.report, "icon": icon, "tone": tone,
                "prefix": "", "suffix": suffix,
            })

        changes = {
            Report.IN_PROGRESS: ("bi-tools", "amber", " is now in progress"),
            Report.PROBLEM_FIXED: ("bi-wrench-adjustable", "sky", " was marked as fixed"),
            Report.RESOLVED: ("bi-check2-circle", "teal", " has been resolved"),
            Report.CLOSED: ("bi-lock", "slate", " was closed"),
        }
        labels = dict(Report.OPERATIONAL_STATUS)
        for h in (
            ReportStatusHistory.objects.filter(report__reporter=user)
            .select_related("report")
            .order_by("-changed_at")[:n]
        ):
            icon, tone, suffix = changes.get(
                h.new_status,
                ("bi-arrow-right-circle", "slate", f" moved to {labels.get(h.new_status, h.new_status)}"),
            )
            events.append({
                "when": h.changed_at, "report": h.report, "icon": icon, "tone": tone,
                "prefix": "", "suffix": suffix,
            })

        events.sort(key=lambda e: e["when"], reverse=True)
        return events[:n]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.db.models import Count, Q

        from reports.models import Report

        user = self.request.user
        mine = Report.objects.filter(reporter=user)

        # Recent reports (existing context name kept: my_reports).
        recent = list(
            mine.select_related("category", "area", "verification").order_by("-created_at")[
                : self.reports_shown
            ]
        )
        for report in recent:
            report.progress = self._progress(report)
        context["my_reports"] = recent

        # Personal impact: counted from the citizen's actual reports.
        agg = mine.aggregate(
            total=Count("id"),
            resolved=Count("id", filter=Q(operational_status=Report.RESOLVED)),
            in_progress=Count("id", filter=Q(operational_status=Report.IN_PROGRESS)),
        )
        context["my_reports_total"] = agg["total"]
        context["impact"] = {
            **agg,
            # None when nothing has been reported, so no fake 0% is shown.
            "rate": round(agg["resolved"] / agg["total"] * 100) if agg["total"] else None,
        }
        context["activity"] = self._activity(user)
        return context


class AuthorityDashboardView(ApprovedAuthorityRequiredMixin, TemplateView):
    template_name = "accounts/authority_dashboard.html"
    paginate_by = 8
    MONTHS_SHOWN = 6

    # ---- helpers ------------------------------------------------------------
    @staticmethod
    def _format_duration(delta):
        """timedelta -> '2.5 days' / '6 hrs' / '20 min' (None stays None)."""
        if delta is None:
            return None
        seconds = delta.total_seconds()
        if seconds >= 86400:
            value, unit = seconds / 86400, "day"
        elif seconds >= 3600:
            value, unit = seconds / 3600, "hr"
        else:
            value, unit = max(seconds / 60, 1), "min"
        text = f"{value:.1f}".rstrip("0").rstrip(".")
        plural = "s" if unit in ("day", "hr") and text != "1" else ""
        return f"{text} {unit}{plural}"

    def _monthly_overview(self, area_reports):
        """Reports received vs. resolved per month, from real records only."""
        from datetime import datetime

        from django.db.models import Count
        from django.db.models.functions import TruncMonth
        from django.utils import timezone

        from reports.models import Report

        today = timezone.localdate()
        months = []
        year, month = today.year, today.month
        for _ in range(self.MONTHS_SHOWN):
            months.append((year, month))
            month -= 1
            if month == 0:
                year, month = year - 1, 12
        months.reverse()
        start = timezone.make_aware(datetime(months[0][0], months[0][1], 1))

        def per_month(qs, field):
            rows = (
                qs.filter(**{f"{field}__gte": start})
                .annotate(m=TruncMonth(field))
                .order_by("m")  # clears Report.Meta.ordering so GROUP BY works
                .values("m")
                .annotate(n=Count("id"))
            )
            return {(r["m"].year, r["m"].month): r["n"] for r in rows}

        received = per_month(area_reports, "created_at")
        resolved = per_month(
            area_reports.filter(operational_status=Report.RESOLVED), "resolved_at"
        )

        peak = max([1, *received.values(), *resolved.values()])
        data = []
        for y, m in months:
            r, s = received.get((y, m), 0), resolved.get((y, m), 0)
            data.append({
                "label": datetime(y, m, 1).strftime("%b"),
                "year": y,
                "received": r,
                "resolved": s,
                "received_pct": round(r / peak * 100),
                "resolved_pct": round(s / peak * 100),
            })
        return data

    # ---- context ------------------------------------------------------------
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        from django.core.paginator import Paginator
        from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F, Q

        from core.models import Category
        from reports.models import Report
        from reports.permissions import reports_in_authority_area

        from .forms import AuthorityReportFilterForm

        profile = self.request.user.authority_profile
        context["profile"] = profile

        # Single source of truth: only this authority's own area (existing rule).
        area_reports = reports_in_authority_area(self.request.user)

        # --- stat cards + performance numbers (same status logic as before) ---
        agg = area_reports.aggregate(
            total=Count("id"),
            pending=Count("id", filter=Q(operational_status=Report.REPORTED)),
            in_progress=Count("id", filter=Q(operational_status=Report.IN_PROGRESS)),
            resolved=Count("id", filter=Q(operational_status=Report.RESOLVED)),
            needs_verification=Count("id", filter=Q(verification_status="pending")),
            avg_resolution=Avg(
                ExpressionWrapper(F("resolved_at") - F("created_at"), output_field=DurationField()),
                filter=Q(operational_status=Report.RESOLVED, resolved_at__isnull=False),
            ),
        )
        context["stats"] = {
            k: agg[k] for k in ("pending", "in_progress", "resolved", "needs_verification")
        }
        total, resolved = agg["total"], agg["resolved"]
        context["performance"] = {
            "total": total,
            "resolved": resolved,
            "pending": agg["pending"],
            # None when there are no reports, so the template never shows a fake 0%.
            "rate": round(resolved / total * 100, 1) if total else None,
            "avg_resolution": self._format_duration(agg["avg_resolution"]),
            "monthly": self._monthly_overview(area_reports),
        }
        context["show_monthly"] = any(
            m["received"] or m["resolved"] for m in context["performance"]["monthly"]
        )

        # --- Recent Reports: search, filters, pagination ---
        categories = Category.objects.filter(
            pk__in=area_reports.order_by().values("category_id")
        )
        form = AuthorityReportFilterForm(self.request.GET, category_queryset=categories)
        form.is_valid()  # invalid fields are simply left out of cleaned_data
        data = form.cleaned_data

        status_filters = {
            "pending": Q(operational_status=Report.REPORTED),
            "in_progress": Q(operational_status=Report.IN_PROGRESS),
            "problem_fixed": Q(operational_status=Report.PROBLEM_FIXED),
            "resolved": Q(operational_status=Report.RESOLVED),
            "closed": Q(operational_status=Report.CLOSED),
            "needs_verification": Q(verification_status="pending"),
        }

        reports = area_reports
        if data.get("q"):
            term = data["q"].strip()
            reports = reports.filter(
                Q(title__icontains=term)
                | Q(location_text__icontains=term)
                | Q(category__name__icontains=term)
                | Q(description__icontains=term)
            )
        if data.get("status") in status_filters:
            reports = reports.filter(status_filters[data["status"]])
        if data.get("category"):
            reports = reports.filter(category=data["category"])

        page_obj = Paginator(reports.order_by("-created_at", "-pk"), self.paginate_by).get_page(
            self.request.GET.get("page")
        )

        params = self.request.GET.copy()
        params.pop("page", None)

        context.update(
            recent_reports=page_obj,
            page_obj=page_obj,
            filter_form=form,
            filters_active=bool(data.get("q") or data.get("status") or data.get("category")),
            querystring=params.urlencode(),
        )
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