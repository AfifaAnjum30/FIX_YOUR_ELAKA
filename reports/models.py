from django.db import models
from django.db import models
from django.core.exceptions import ValidationError

# Create your models here.
import os
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils import timezone

from .signals import report_status_changed
from .validators import validate_image_file


def _unique_path(folder, filename):

    ext = os.path.splitext(filename)[1].lower()
    return f"reports/{folder}/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext}"


def before_image_path(instance, filename):
    return _unique_path("before", filename)


def after_image_path(instance, filename):
    return _unique_path("after", filename)



class Report(models.Model):

    REPORTED = "reported"
    IN_PROGRESS = "in_progress"
    PROBLEM_FIXED = "problem_fixed"
    RESOLVED = "resolved"
    CLOSED = "closed"

    OPERATIONAL_STATUS = (
        (REPORTED, "Reported"),
        (IN_PROGRESS, "In Progress"),
        (PROBLEM_FIXED, "Problem Fixed"),
        (RESOLVED, "Resolved"),
        (CLOSED, "Closed"),
    )

    VERIFICATION_STATUS = (
        ("pending", "Pending"),
        ("verified", "Verified"),
        ("rejected", "Rejected"),
    )

    PHYSICAL_TRANSITIONS = {
        REPORTED: (IN_PROGRESS,),
        IN_PROGRESS: (PROBLEM_FIXED,),
        PROBLEM_FIXED: (RESOLVED,),
        RESOLVED: (),
        CLOSED: (),
    }
    SAFETY_TRANSITIONS = {
        REPORTED: (IN_PROGRESS, CLOSED),
        IN_PROGRESS: (CLOSED,),
        PROBLEM_FIXED: (),
        RESOLVED: (),
        CLOSED: (),
    }
    PHYSICAL_WORKFLOW = (REPORTED, IN_PROGRESS, PROBLEM_FIXED, RESOLVED)
    SAFETY_WORKFLOW = (REPORTED, IN_PROGRESS, CLOSED)

    title = models.CharField(max_length=200)
    description = models.TextField()
    reporter = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reports"
    )
    category = models.ForeignKey(
        "core.Category", on_delete=models.PROTECT, related_name="reports"
    )
    area = models.ForeignKey(
        "core.Area", on_delete=models.PROTECT, related_name="reports"
    )
    location_text = models.CharField(
        max_length=255, help_text="Human-readable location, e.g. 'Road 5, near the mosque'"
    )
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )
    before_image = models.ImageField(
        upload_to=before_image_path, validators=[validate_image_file]
    )
    after_image = models.ImageField(
        upload_to=after_image_path,
        blank=True,
        null=True,
        validators=[validate_image_file],
    )
    operational_status = models.CharField(
        max_length=20, choices=OPERATIONAL_STATUS, default=REPORTED, db_index=True
    )
    verification_status = models.CharField(
        max_length=20, choices=VERIFICATION_STATUS, default="pending", db_index=True
    )
    priority_score = models.FloatField(default=0.0)
    resolution_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-priority_score", "-created_at"]

    def __str__(self):
        return f"#{self.pk} {self.title}"

    def get_absolute_url(self):
        return reverse("reports:detail", kwargs={"pk": self.pk})


    @property
    def is_safety(self):
        return self.category_id is not None and self.category.type == "safety"

    @property
    def is_verified(self):
        return self.verification_status == "verified"

    @property
    def workflow_steps(self):
       
        return self.SAFETY_WORKFLOW if self.is_safety else self.PHYSICAL_WORKFLOW


    def clean(self):

        if (
            self.operational_status == self.RESOLVED
            and self.category_id
            and self.category.requires_after_photo
            and not self.after_image
        ):
            raise ValidationError(
                "After photo is mandatory for physical infrastructure reports "
                "before marking Resolved."
            )

    def _transition_map(self):
        return self.SAFETY_TRANSITIONS if self.is_safety else self.PHYSICAL_TRANSITIONS

    def allowed_next_statuses(self):
        """Statuses this report may move to next, ignoring verification and
        photo rules (use can_transition_to() for the full check)."""
        return list(self._transition_map().get(self.operational_status, ()))

    def transition_error(self, new_status):
        """Return a human-readable reason the move is not allowed, or None."""
        if new_status not in dict(self.OPERATIONAL_STATUS):
            return f"'{new_status}' is not a valid status."

        if new_status not in self.allowed_next_statuses():
            current = self.get_operational_status_display()
            target = dict(self.OPERATIONAL_STATUS)[new_status]
            return f"A report cannot move from {current} to {target}."


        if self.operational_status == self.REPORTED and new_status == self.CLOSED:
            if self.verification_status == "pending":
                return "Review (verify or reject) this report before closing it."
        elif not self.is_verified:
            return "Only verified reports can move forward. Verify the report first."

        if new_status == self.RESOLVED:
            if self.category.requires_after_photo and not self.after_image:
                return (
                    "An after photo is mandatory before a physical-repair "
                    "report can be marked Resolved."
                )
        return None

    def can_transition_to(self, new_status):
        return self.transition_error(new_status) is None

    def transition_to(self, new_status, user=None, remarks=""):

        error = self.transition_error(new_status)
        if error:
            raise ValidationError(error)

        previous = self.operational_status
        self.operational_status = new_status
        update_fields = ["operational_status", "updated_at"]
        if new_status in (self.RESOLVED, self.CLOSED):
            self.resolved_at = timezone.now()
            update_fields.append("resolved_at")
        if remarks and new_status in (self.RESOLVED, self.CLOSED):
            self.resolution_note = remarks
            update_fields.append("resolution_note")
        self.save(update_fields=update_fields)

        report_status_changed.send(
            sender=self.__class__,
            instance=self,
            previous_status=previous,
            new_status=new_status,
            changed_by=user,
            remarks=remarks,
        )
        return previous


class Verification(models.Model):
        report = models.OneToOneField(
            'reports.Report',
            on_delete=models.CASCADE,
            related_name='verification'
        )

        reviewed_by = models.ForeignKey(
            'accounts.AuthorityProfile',
            on_delete=models.SET_NULL,
            null=True,
            related_name='verifications'
        )

        status = models.CharField(
            max_length=20,
            choices=[
                ('pending', 'Pending'),
                ('verified', 'Verified'),
                ('rejected', 'Rejected'),
            ]
        )

        remarks = models.TextField(blank=True)
        verified_at = models.DateTimeField(auto_now=True)

        def __str__(self):
            return f"{self.report.title} - {self.status}"

class ReportStatusHistory(models.Model):
        report = models.ForeignKey(
            'reports.Report',
            on_delete=models.CASCADE,
            related_name='status_history'
        )

        previous_status = models.CharField(max_length=20)
        new_status = models.CharField(max_length=20)

        changed_by = models.ForeignKey(
            'accounts.AuthorityProfile',
            on_delete=models.SET_NULL,
            null=True,
            related_name='status_changes'
        )

        remarks = models.TextField(blank=True)
        changed_at = models.DateTimeField(auto_now_add=True)

        class Meta:
            ordering = ['-changed_at']

        def __str__(self):
            return f"{self.report.title}: {self.previous_status} -> {self.new_status}"


