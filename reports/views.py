from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.generic import CreateView, DetailView, ListView

from accounts.mixins import CitizenRequiredMixin
from core.forms import ReportFilterForm
from .forms import ReportCreateForm, VerificationForm, ReportStatusForm
from .models import Report, Verification, ReportStatusHistory
from .permissions import can_manage_report, visible_reports_for
from accounts.models import AuthorityProfile
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .models import Report, Verification
from .forms import VerificationForm


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

    def get_authority(user):
        if not user.is_authenticated or user.role != 'authority':
            return None

        try:
            profile = user.authority_profile
        except AuthorityProfile.DoesNotExist:
            return None

        if profile.approval_status != 'approved':
            return None

        return profile

    def can_process_report(authority, report):
        return (
                authority is not None
                and authority.assigned_area_id == report.area_id
        )

    @login_required
    def verify_report(request, report_id):
        report = get_object_or_404(Report, pk=report_id)
        authority = request.get_authority(request.user)

        if not request.can_process_report(authority, report):
            messages.error(
                request,
                "You are not authorized to verify this report."
            )
            return redirect('report-list')

        if request.method == 'POST':
            form = VerificationForm(request.POST)

            if form.is_valid():
                decision = form.cleaned_data['status']

                with transaction.atomic():
                    verification, created = Verification.objects.get_or_create(
                        report=report,
                        defaults={
                            'reviewed_by': authority,
                            'status': decision,
                            'remarks': form.cleaned_data['remarks'],
                        }
                    )

                    if not created:
                        verification.reviewed_by = authority
                        verification.status = decision
                        verification.remarks = form.cleaned_data['remarks']
                        verification.save()

                    report.verification_status = decision
                    report.save(update_fields=['verification_status'])

                    if decision == 'verified' and created:
                        reporter = report.reporter

                        reporter.verified_reports_count += 1
                        reporter.save(update_fields=['verified_reports_count'])

                        reporter.update_trust_score()

                messages.success(request, 'Verification saved.')
                return redirect('report-list')

        else:
            form = VerificationForm()

        return render(
            request,
            'reports/verify_report.html',
            {'form': form, 'report': report}
        )

@login_required
def update_report_status(request, report_id, updated_report=None):
        report = get_object_or_404(Report, pk=report_id)
        authority = request.get_authority(request.user)
        updated_report.resolved_at = timezone.now()

        if not request.can_process_report(authority, report):
            messages.error(
                request,
                "You are not authorized to update this report."
            )
            return redirect('report-list')

        if report.verification_status != 'verified':
            messages.error(
                request,
                "Verify the report before updating its status."
            )
            return redirect('report-list')

        if request.method == 'POST':
            form = ReportStatusForm(
                request.POST,
                request.FILES,
                instance=report
            )

            if form.is_valid():
                old_status = report.operational_status

                with transaction.atomic():
                    updated_report = form.save(commit=False)

                    try:
                        updated_report.full_clean()
                    except ValidationError as error:
                        form.add_error(None, error)
                    else:
                        updated_report.save()

                        if old_status != updated_report.operational_status:
                            ReportStatusHistory.objects.create(
                                report=updated_report,
                                previous_status=old_status,
                                new_status=updated_report.operational_status,
                                changed_by=authority,
                                remarks=updated_report.resolution_note,
                            )

                            if updated_report.operational_status == 'resolved':
                                updated_report.resolved_at = (
                                    __import__('django.utils.timezone',
                                               fromlist=['now']).now()
                                )
                                updated_report.save(
                                    update_fields=['resolved_at']
                                )

                        messages.success(
                            request,
                            'Report status updated successfully.'
                        )
                        return redirect('report-list')

        else:
            form = ReportStatusForm(instance=report)

        return render(
            request,
            'reports/update_status.html',
            {'form': form, 'report': report}
        )


@login_required
def verify_report(request, report_id):
        report = get_object_or_404(Report, pk=report_id)

        if request.method == 'POST':
            form = VerificationForm(request.POST)

            if form.is_valid():
                decision = form.cleaned_data['status']

                Verification.objects.update_or_create(
                    report=report,
                    defaults={
                        'status': decision,
                        'remarks': form.cleaned_data.get('remarks', ''),
                    }
                )

                report.verification_status = decision
                report.save(update_fields=['verification_status'])

                messages.success(request, 'Verification saved.')
                return redirect('report-list')

        else:
            form = VerificationForm()

        return render(
            request,
            'reports/verify_report.html',
            {'form': form, 'report': report}
        )