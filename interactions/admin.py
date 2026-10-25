from django.contrib import admin

from .models import Comment, Vote


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "user", "short_text", "created_at")
    list_filter = ("created_at",)
    search_fields = ("text", "user__username", "user__email", "report__title")
    list_select_related = ("report", "user")
    readonly_fields = ("created_at", "updated_at")
    date_hierarchy = "created_at"

    @admin.display(description="Text")
    def short_text(self, obj: Comment) -> str:
        return obj.text[:60] + ("..." if len(obj.text) > 60 else "")


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = ("id", "report", "user", "vote_value", "created_at", "updated_at")
    list_filter = ("vote_value", "created_at")
    search_fields = ("user__username", "user__email", "report__title")
    list_select_related = ("report", "user")
    readonly_fields = ("created_at", "updated_at")