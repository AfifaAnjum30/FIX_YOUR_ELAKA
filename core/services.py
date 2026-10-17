from django.apps import apps
from django.db.models import Q


def public_reports(filters=None):
    """Return public reports only. No reports app yet => None.

    Safety reports are excluded until the team implements a reviewed,
    privacy-safe publication policy.
    """
    if not apps.is_installed('reports'):
        return None
    Report = apps.get_model('reports', 'Report')
    qs = Report.objects.select_related('area', 'category').exclude(category__type='safety')
    # Pending/rejected reports are not publicly exposed.
    qs = qs.filter(verification_status='verified')
    filters = filters or {}
    if filters.get('q'):
        qs = qs.filter(Q(title__icontains=filters['q']) | Q(description__icontains=filters['q']))
    if filters.get('area'):
        qs = qs.filter(area=filters['area'])
    if filters.get('category'):
        qs = qs.filter(category=filters['category'])
    if filters.get('status'):
        qs = qs.filter(operational_status=filters['status'])
    return qs.order_by('-created_at')
