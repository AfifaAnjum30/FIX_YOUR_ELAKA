from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Count, Q, Sum


class Comment(models.Model):
    """A comment left by a user on a report."""

    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.CASCADE,
        related_name="comments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
    )
    text = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [models.Index(fields=["report", "created_at"])]

    def __str__(self) -> str:
        preview = self.text[:40] + ("..." if len(self.text) > 40 else "")
        return f"Comment by {self.user} on report #{self.report_id}: {preview}"


class VoteQuerySet(models.QuerySet):
    """Aggregate helpers, usable as report.votes.summary()."""

    def summary(self) -> dict[str, int]:
        """Return {'upvotes': n, 'downvotes': n, 'score': n}. score = up - down."""
        data = self.aggregate(
            upvotes=Count("pk", filter=Q(vote_value=1)),
            downvotes=Count("pk", filter=Q(vote_value=-1)),
            score=Sum("vote_value"),
        )
        return {
            "upvotes": data["upvotes"] or 0,
            "downvotes": data["downvotes"] or 0,
            "score": data["score"] or 0,
        }


class Vote(models.Model):
    """
    One vote per (user, report), enforced by the database.
    Net score is informational: downvotes alone never mark a report as false.
    """

    class Value(models.IntegerChoices):
        UPVOTE = 1, "Upvote"
        DOWNVOTE = -1, "Downvote"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="votes",
    )
    report = models.ForeignKey(
        "reports.Report",
        on_delete=models.CASCADE,
        related_name="votes",
    )
    vote_value = models.SmallIntegerField(choices=Value.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = VoteQuerySet.as_manager()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "report"], name="unique_vote_per_user_per_report"
            ),
            models.CheckConstraint(
                condition=Q(vote_value__in=[1, -1]),   # Django 6.x syntax
                name="vote_value_is_plus_or_minus_one",
            ),
        ]
        indexes = [models.Index(fields=["report", "user"])]

    def __str__(self) -> str:
        return f"{self.user} -> report #{self.report_id}: {self.get_vote_value_display()}"

    @property
    def is_upvote(self) -> bool:
        return self.vote_value == self.Value.UPVOTE

    @property
    def is_downvote(self) -> bool:
        return self.vote_value == self.Value.DOWNVOTE