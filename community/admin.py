from django.contrib import admin

from .models import GlobalChatMessage


@admin.register(GlobalChatMessage)
class GlobalChatMessageAdmin(admin.ModelAdmin):
    """Expose chat evidence to authorized staff without mutation actions."""

    list_display = ("id", "sender", "body_preview", "created_at")
    list_select_related = ("sender",)
    search_fields = ("sender__username", "body")
    ordering = ("-created_at", "-id")
    date_hierarchy = "created_at"
    fields = ("sender", "body", "created_at")
    readonly_fields = fields

    @admin.display(description="메시지")
    def body_preview(self, obj):
        return obj.body[:80]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
