from django.shortcuts import render

# Create your views here.
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F, Q
from django.views.generic import CreateView, DetailView, ListView

from accounts.mixins import CitizenRequiredMixin
from core.forms import ReportFilterForm

from .forms import ReportCreateForm
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