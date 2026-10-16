from django.contrib import messages
from django.contrib.auth.mixins import AccessMixin
from django.shortcuts import redirect


class RoleRequiredMixin(AccessMixin):
    """
    Base class. Checks happen SERVER-SIDE in dispatch(), so typing a URL
    manually cannot bypass them.
      - anonymous        -> redirect to login (with ?next=)
      - wrong role       -> error message + redirect to the user's own dashboard
      - extra_check fail -> whatever response extra_check returns
    """

    required_role = None
    permission_denied_message = "You do not have permission to view that page."

    def extra_check(self, request):
        """Subclasses may return an HttpResponse to block access, or None to allow."""
        return None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()  # redirects to LOGIN_URL

        if request.user.role != self.required_role:
            messages.error(request, self.permission_denied_message)
            return redirect("accounts:dashboard")  # role router, no redirect loop

        denied = self.extra_check(request)
        if denied is not None:
            return denied

        return super().dispatch(request, *args, **kwargs)


class CitizenRequiredMixin(RoleRequiredMixin):
    required_role = "citizen"
    permission_denied_message = "That page is for citizens only."


class AuthorityRequiredMixin(RoleRequiredMixin):
    """Role = authority, regardless of approval (used by the 'pending approval' page)."""
    required_role = "authority"
    permission_denied_message = "That page is for authority accounts only."


class ApprovedAuthorityRequiredMixin(AuthorityRequiredMixin):
    """Role = authority AND approval_status == 'approved'."""

    def extra_check(self, request):
        if not request.user.is_approved_authority:
            messages.warning(
                request, "Your authority account is not approved yet."
            )
            return redirect("accounts:pending_approval")
        # FUTURE: when reports exist, also enforce report.area == profile.assigned_area here
        return None


class AdminRequiredMixin(RoleRequiredMixin):
    required_role = "admin"
    permission_denied_message = "Administrator access required."


class AnonymousOnlyMixin:
    """For login/register pages: logged-in users are sent to their dashboard."""

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect("accounts:dashboard")
        return super().dispatch(request, *args, **kwargs)