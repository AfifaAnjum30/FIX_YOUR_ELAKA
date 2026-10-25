from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, ListView

from accounts.mixins import CitizenRequiredMixin
from core.forms import ReportFilterForm

from .forms import ReportCreateForm, ReportStatusForm, VerificationForm
from .models import Report, ReportStatusHistory, Verification
from .permissions import can_manage_report, visible_reports_for


class ReportListView(ListView):


    template_name = "reports/report_list.html"
    context_object_name = "reports"
    paginate_by = 10

    def get_queryset(self):
        user = self.request.user
        qs = visible_reports_for(user)

        scope = self.request.GET.get("scope", "all")
        if scope == "mine" and user.is_authenticated:
            qs = qs.filter(reporter=user)
        elif scope == "area" and user.is_authenticated and user.is_approved_authority:
            qs = qs.filter(area__name__iexact=user.authority_profile.assigned_area_name.strip())
        else:
            scope = "all"
        self.scope = scope

        self.filter_form = ReportFilterForm(self.request.GET)
        if self.filter_form.is_valid():
            data = self.filter_form.cleaned_data
            if data.get("q"):
                qs = qs.filter(Q(title__icontains=data["q"]) | Q(description__icontains=data["q"]))
            if data.get("area"):
                qs = qs.filter(area=data["area"])
            if data.get("category"):
                qs = qs.filter(category=data["category"])
            if data.get("status"):
                qs = qs.filter(operational_status=data["status"])
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = self.filter_form
        ctx["scope"] = self.scope

        params = self.request.GET.copy()
        params.pop("page", None)
        ctx["querystring"] = params.urlencode()
        return ctx


class ReportDetailView(DetailView):
    template_name = "reports/report_detail.html"
    context_object_name = "report"

    def get_queryset(self):
        # Reports the user may not see simply 404.
        return visible_reports_for(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        report = self.object
        user = self.request.user
        ctx["workflow_steps"] = [
            (key, dict(report.OPERATIONAL_STATUS)[key]) for key in report.workflow_steps
        ]
        ctx["is_owner"] = user.is_authenticated and report.reporter_id == user.pk
        ctx["can_manage"] = can_manage_report(user, report)
        return ctx


class ReportCreateView(CitizenRequiredMixin, CreateView):


    form_class = ReportCreateForm
    template_name = "reports/report_form.html"

    @transaction.atomic
    def form_valid(self, form):
        user = self.request.user
        
        form.instance.reporter = user
        response = super().form_valid(form)


        get_user_model().objects.filter(pk=user.pk).update(
            total_reports_count=F("total_reports_count") + 1
        )
        user.refresh_from_db()
        user.update_trust_score()

        messages.success(
            self.request,
            "Thank you! Your report was submitted. It becomes public once an "
            "authority has verified it.",
        )
        return response

    # ---------------------------------------------------------------------------
    # Authority actions
    # ---------------------------------------------------------------------------


@login_required
def verify_report(request, report_id):
    """An approved authority in the report's area verifies or rejects it."""
    report = get_object_or_404(Report, pk=report_id)

    # can_manage_report: approved authority AND assigned area matches report area
    if not can_manage_report(request.user, report):
        messages.error(request, "You are not authorized to verify this report.")
        return redirect("reports:list")

    authority = request.user.authority_profile_or_none

    if request.method == "POST":
        form = VerificationForm(request.POST)
        if form.is_valid():
            decision = form.cleaned_data["status"]
            was_verified = report.verification_status == "verified"

            with transaction.atomic():
                Verification.objects.update_or_create(
                    report=report,
                    defaults={
                        "reviewed_by": authority,
                        "status": decision,
                        "remarks": form.cleaned_data["remarks"],
                    },
                )
                report.verification_status = decision
                report.save(update_fields=["verification_status", "updated_at"])

                # Keep the reporter's trust-score counters in step.
                reporter_qs = get_user_model().objects.filter(pk=report.reporter_id)
                if decision == "verified" and not was_verified:
                    reporter_qs.update(
                        verified_reports_count=F("verified_reports_count") + 1
                    )
                elif was_verified and decision != "verified":
                    reporter_qs.filter(verified_reports_count__gt=0).update(
                        verified_reports_count=F("verified_reports_count") - 1
                    )

            report.reporter.refresh_from_db()
            report.reporter.update_trust_score()

            messages.success(request, "Verification saved.")
            return redirect(report.get_absolute_url())
    else:
        form = VerificationForm()

    return render(request, "reports/verify_report.html", {"form": form, "report": report})


@login_required
def update_report_status(request, report_id):
    """An approved authority in the report's area moves it along its workflow."""
    report = get_object_or_404(Report, pk=report_id)

    if not can_manage_report(request.user, report):
        messages.error(request, "You are not authorized to update this report.")
        return redirect("reports:list")

    if report.verification_status == "pending":
        messages.error(request, "Verify the report before updating its status.")
        return redirect(report.get_absolute_url())

    authority = request.user.authority_profile_or_none
    old_status = report.operational_status  # capture BEFORE the form touches the instance

    if request.method == "POST":
        form = ReportStatusForm(request.POST, request.FILES, instance=report)
        if form.is_valid():
            new_status = form.cleaned_data["operational_status"]

            # A ModelForm changes the instance while validating, so put the old
            # status back and let the model judge the move (workflow order,
            # verification rule, mandatory after-photo rule).
            report.operational_status = old_status
            error = (
                None if new_status == old_status else report.transition_error(new_status)
            )

            if error:
                form.add_error("operational_status", error)
            else:
                with transaction.atomic():
                    # Save the after photo and note first...
                    report.save(
                        update_fields=["after_image", "resolution_note", "updated_at"]
                    )
                    # ...then change status (sets resolved_at, sends the signal).
                    if new_status != old_status:
                        report.transition_to(
                            new_status,
                            user=request.user,
                            remarks=report.resolution_note,
                        )
                        ReportStatusHistory.objects.create(
                            report=report,
                            previous_status=old_status,
                            new_status=new_status,
                            changed_by=authority,
                            remarks=report.resolution_note,
                        )
                messages.success(request, "Report status updated successfully.")
                return redirect(report.get_absolute_url())
    else:
        form = ReportStatusForm(instance=report)

    return render(request, "reports/update_status.html", {"form": form, "report": report})