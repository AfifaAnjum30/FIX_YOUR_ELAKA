from django import template
from django.utils import timezone

register = template.Library()

_UNITS = (
    ("year", 365 * 24 * 3600),
    ("month", 30 * 24 * 3600),
    ("week", 7 * 24 * 3600),
    ("day", 24 * 3600),
    ("hour", 3600),
    ("minute", 60),
)


@register.filter
def short_timesince(value):
    """'3 days ago' instead of Django's '3 days, 4 hours' (one unit only)."""
    if not value:
        return ""
    seconds = int((timezone.now() - value).total_seconds())
    for name, size in _UNITS:
        count = seconds // size
        if count >= 1:
            return f"{count} {name}{'s' if count != 1 else ''} ago"
    return "Just now"