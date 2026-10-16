from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.utils import timezone

from .forms import CustomUserChangeForm, CustomUserCreationForm
from .models import AuthorityProfile, User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = User

    list_display = ("username", "email", "first_name", "last_name", "role", "trust_score", "is_active")
    list_filter = ("role", "is_active", "is_staff")
    search_fields = ("username", "email", "first_name", "last_name")

    # Add our custom fields to the edit page
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("FixIt Local", {"fields": ("role", "verified_reports_count", "total_reports_count", "trust_score")}),
    )
    # Fields shown on the "Add user" page
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )


@admin.register(AuthorityProfile)
class AuthorityProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "department", "assigned_area_name", "approval_status", "approved_by", "approved_at")
    list_filter = ("approval_status", "department")
    search_fields = ("user__username", "user__email", "department", "assigned_area_name")
    readonly_fields = ("approved_by", "approved_at")
    actions = ["approve_selected", "reject_selected"]

    def save_model(self, request, obj, form, change):
        """If an admin changes the status on the edit page, stamp who/when automatically."""
        if "approval_status" in form.changed_data:
            if obj.approval_status == AuthorityProfile.ApprovalStatus.APPROVED:
                obj.approved_by = request.user
                obj.approved_at = timezone.now()
                obj.rejection_reason = ""
            else:
                obj.approved_by = None
                obj.approved_at = None
        super().save_model(request, obj, form, change)

    @admin.action(description="Approve selected authority applications", permissions=["change"])
    def approve_selected(self, request, queryset):
        updated = queryset.update(
            approval_status=AuthorityProfile.ApprovalStatus.APPROVED,
            approved_by=request.user,
            approved_at=timezone.now(),
            rejection_reason="",
        )
        self.message_user(request, f"{updated} application(s) approved.", messages.SUCCESS)

    @admin.action(description="Reject selected authority applications", permissions=["change"])
    def reject_selected(self, request, queryset):
        updated = queryset.update(
            approval_status=AuthorityProfile.ApprovalStatus.REJECTED,
            approved_by=None,
            approved_at=None,
            rejection_reason="Rejected by administrator (bulk action).",
        )
        self.message_user(
            request,
            f"{updated} application(s) rejected. Edit an individual profile to add a specific reason.",
            messages.WARNING,
        )