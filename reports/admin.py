from django.contrib import admin

# Register your models here.
from django.contrib import admin

from .models import Report


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "category", "area", "reporter",
        "operational_status", "verification_status", "priority_score", "created_at",
    )
    list_filter = ("operational_status", "verification_status", "category__type", "area")
    search_fields = ("title", "description", "location_text", "reporter__username")
    readonly_fields = ("created_at", "updated_at", "resolved_at")
    date_hierarchy = "created_at"