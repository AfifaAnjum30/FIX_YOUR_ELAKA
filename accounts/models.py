from decimal import Decimal

from django.contrib.auth.models import AbstractUser, UserManager
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils import timezone


class FixItUserManager(UserManager):
    """
    Makes `createsuperuser` produce a user with role='admin', so a superuser
    is automatically a FixIt Local Administrator.
    """

    def create_superuser(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault("role", User.Role.ADMIN)
        return super().create_superuser(username, email, password, **extra_fields)


class User(AbstractUser):
    """Custom user. Always define this at project start."""

    class Role(models.TextChoices):
        CITIZEN = "citizen", "Citizen"
        AUTHORITY = "authority", "Authority"
        ADMIN = "admin", "Administrator"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CITIZEN)

    # Reporter Trust Score fields
    verified_reports_count = models.PositiveIntegerField(default=0)
    total_reports_count = models.PositiveIntegerField(default=0)
    trust_score = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    objects = FixItUserManager()

    def __str__(self):
        return self.get_full_name() or self.username

    # ---- Role helpers (kept separate from is_staff / is_superuser on purpose) ----
    @property
    def is_citizen(self):
        return self.role == self.Role.CITIZEN

    @property
    def is_authority(self):
        return self.role == self.Role.AUTHORITY

    @property
    def is_platform_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def authority_profile_or_none(self):
        """Returns the AuthorityProfile or None (avoids RelatedObjectDoesNotExist)."""
        try:
            return self.authority_profile
        except ObjectDoesNotExist:
            return None

    @property
    def is_approved_authority(self):
        profile = self.authority_profile_or_none
        return (
            self.is_authority
            and profile is not None
            and profile.approval_status == AuthorityProfile.ApprovalStatus.APPROVED
        )

    # ---- Trust score ----
    def update_trust_score(self):
        """Trust Score = (verified / total) * 100. Zero reports => 0 (shown as 'Not Yet Rated')."""
        if self.total_reports_count == 0:
            self.trust_score = Decimal("0.00")
        else:
            score = Decimal(self.verified_reports_count) / Decimal(self.total_reports_count) * 100
            self.trust_score = min(score, Decimal("100")).quantize(Decimal("0.01"))
        self.save(update_fields=["trust_score"])

    @property
    def trust_score_display(self):
        if self.total_reports_count == 0:
            return "Not Yet Rated"
        return f"{self.trust_score}%"


class AuthorityProfile(models.Model):
    class ApprovalStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="authority_profile"
    )
    department = models.CharField(max_length=150)
    # TEMPORARY: replace with ForeignKey('core.Area') once the core app exists.
    assigned_area_name = models.CharField(max_length=100)

    approval_status = models.CharField(
        max_length=20,
        choices=ApprovalStatus.choices,
        default=ApprovalStatus.PENDING,
        db_index=True,
    )
    approved_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="approved_authorities",
        limit_choices_to={"role": User.Role.ADMIN},
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        verbose_name = "Authority Profile"
        verbose_name_plural = "Authority Profiles"

    def __str__(self):
        return f"{self.user} - {self.department} ({self.get_approval_status_display()})"

    def approve(self, admin_user):
        self.approval_status = self.ApprovalStatus.APPROVED
        self.approved_by = admin_user
        self.approved_at = timezone.now()
        self.rejection_reason = ""
        self.save()

    def reject(self, admin_user, reason=""):
        self.approval_status = self.ApprovalStatus.REJECTED
        self.approved_by = None
        self.approved_at = None
        self.rejection_reason = reason
        self.save()