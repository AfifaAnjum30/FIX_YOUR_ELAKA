
from django.db.models import Q

from .models import Report


def _authority_area_name(user):

    if not user.is_authenticated or not user.is_approved_authority:
        return None
    name = user.authority_profile.assigned_area_name.strip()
    return name or None



def visible_reports_for(user):
    qs = Report.objects.select_related("area", "category", "reporter")

    if user.is_authenticated and user.is_platform_admin:
        return qs

    # Show verified, non-safety reports publicly.
    condition = Q(verification_status="verified") & ~Q(category__type="safety")

    if user.is_authenticated:
        # Allow members to see reports submitted by everyone.
        condition |= Q(reporter__isnull=False)

        # Preserve authority access to reports in their assigned area.
        area_name = _authority_area_name(user)
        if area_name:
            condition |= Q(area__name__iexact=area_name)

    return qs.filter(condition).distinct()


def reports_in_authority_area(user):

    area_name = _authority_area_name(user)
    if not area_name:
        return Report.objects.none()
    return Report.objects.select_related("area", "category", "reporter").filter(
        area__name__iexact=area_name
    )


def can_manage_report(user, report):
    
    area_name = _authority_area_name(user)
    return bool(area_name) and report.area.name.strip().lower() == area_name.lower()