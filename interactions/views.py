from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from reports.models import Report
from reports.permissions import visible_reports_for

from .forms import CommentForm, VoteForm
from .models import Vote


def _get_visible_report(request: HttpRequest, report_id: int) -> Report:
    """404 unless this user is allowed to see the report (same rules as the detail page)."""
    return get_object_or_404(visible_reports_for(request.user), pk=report_id)


@login_required
@require_POST
def add_comment(request: HttpRequest, report_id: int) -> HttpResponse:
    """Logged-in users add a comment to a report they can see."""
    report = _get_visible_report(request, report_id)
    form = CommentForm(request.POST)

    if form.is_valid():
        comment = form.save(commit=False)
        comment.report = report
        comment.user = request.user
        comment.save()
        messages.success(request, "Your comment was added.")
    else:
        errors = "; ".join(e for errs in form.errors.values() for e in errs)
        messages.error(request, f"Could not add comment: {errors}")

    return redirect(f"{report.get_absolute_url()}#comments")


@login_required
@require_POST
def toggle_vote(request: HttpRequest, report_id: int) -> HttpResponse:
    """
    POST vote_value = 1 or -1.
      no vote yet        -> create
      different value    -> update (user changes their mind)
      same value again   -> delete (toggle off)
    """
    report = _get_visible_report(request, report_id)
    form = VoteForm(request.POST)

    if not form.is_valid():
        messages.error(request, "Invalid vote.")
        return redirect(f"{report.get_absolute_url()}#votes")

    _apply_vote(request.user, report, form.cleaned_data["vote_value"])
    return redirect(f"{report.get_absolute_url()}#votes")


def _apply_vote(user, report: Report, new_value: int) -> int | None:
    """Create / update / delete the user's vote. Returns the resulting value or None."""
    with transaction.atomic():
        vote = Vote.objects.select_for_update().filter(user=user, report=report).first()

        if vote is None:
            try:
                with transaction.atomic():
                    Vote.objects.create(user=user, report=report, vote_value=new_value)
                return new_value
            except IntegrityError:
                # Double-click race: another request created it first.
                vote = Vote.objects.get(user=user, report=report)

        if vote.vote_value == new_value:
            vote.delete()                       # same button again -> remove vote
            return None

        vote.vote_value = new_value             # switch up <-> down
        vote.save(update_fields=["vote_value", "updated_at"])
        return new_value