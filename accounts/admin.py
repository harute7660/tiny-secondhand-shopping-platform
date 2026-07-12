from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from .models import LoginAttempt, User, UserBlock


class ReadOnlyAdminMixin:
    """Expose server-authored security records without mutation controls."""

    def get_readonly_fields(self, request, obj=None):
        return tuple(field.name for field in self.model._meta.concrete_fields)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    privilege_fields = ("is_staff", "is_superuser", "groups", "user_permissions")
    account_state_fields = ("is_active", "is_suspended", "suspension_reason", "suspended_at")
    fieldsets = DjangoUserAdmin.fieldsets + (
        (
            "Suspension",
            {
                "fields": (
                    "is_suspended",
                    "suspension_reason",
                    "suspended_at",
                ),
            },
        ),
    )
    readonly_fields = ("last_login", "date_joined", "suspended_at")
    list_display = (
        "username",
        "email",
        "is_staff",
        "is_active",
        "is_suspended",
    )
    list_filter = DjangoUserAdmin.list_filter + ("is_suspended",)
    actions = ("suspend_selected", "unsuspend_selected")

    def has_suspend_permission(self, request):
        return request.user.has_perm("accounts.suspend_user")

    def _require_suspend_permission(self, request):
        # Keep this check inside each action as well as in get_actions so a
        # crafted changelist POST cannot invoke a hidden action.
        if not self.has_suspend_permission(request):
            raise PermissionDenied

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            readonly.extend(self.privilege_fields)
            readonly.extend(self.account_state_fields)
        return tuple(dict.fromkeys(readonly))

    def has_change_permission(self, request, obj=None):
        if not super().has_change_permission(request, obj):
            return False
        if obj is not None and not request.user.is_superuser:
            return not (obj.is_staff or obj.is_superuser)
        return True

    def has_delete_permission(self, request, obj=None):
        if not super().has_delete_permission(request, obj):
            return False
        if obj is None:
            return True
        if obj.pk == request.user.pk:
            return False
        if not request.user.is_superuser and (obj.is_staff or obj.is_superuser):
            return False
        return True

    def user_change_password(self, request, id, form_url=""):
        # change_user permits profile maintenance, not silent credential
        # takeover. Password reset remains a superuser-only recovery action
        # until a re-authentication, notification, and approval flow exists.
        if not request.user.is_superuser:
            raise PermissionDenied
        return super().user_change_password(request, id, form_url)

    def delete_queryset(self, request, queryset):
        if request.user.is_superuser:
            queryset = queryset.exclude(pk=request.user.pk)
        else:
            queryset = self._ordinary_targets(request, queryset)
        return super().delete_queryset(request, queryset)

    @staticmethod
    def _ordinary_targets(request, queryset):
        """Bulk account state changes may target ordinary users only."""
        return queryset.filter(
            is_staff=False,
            is_superuser=False,
        ).exclude(pk=request.user.pk)

    @admin.action(description="Suspend selected users", permissions=["suspend"])
    def suspend_selected(self, request, queryset):
        self._require_suspend_permission(request)
        with transaction.atomic():
            for user in self._ordinary_targets(request, queryset).select_for_update():
                user.is_suspended = True
                user.is_active = False
                user.suspension_reason = "Suspended by an administrator."
                user.suspended_at = timezone.now()
                user.save(
                    update_fields=(
                        "is_suspended",
                        "is_active",
                        "suspension_reason",
                        "suspended_at",
                    )
                )
                self.log_change(request, user, "관리자가 사용자 계정을 정지했습니다.")

    @admin.action(description="Unsuspend selected users", permissions=["suspend"])
    def unsuspend_selected(self, request, queryset):
        self._require_suspend_permission(request)
        with transaction.atomic():
            targets = (
                self._ordinary_targets(request, queryset)
                .filter(is_suspended=True)
                .select_for_update()
            )
            for user in targets:
                user.is_suspended = False
                user.is_active = True
                user.suspension_reason = ""
                user.suspended_at = None
                user.save(
                    update_fields=(
                        "is_suspended",
                        "is_active",
                        "suspension_reason",
                        "suspended_at",
                    )
                )
                self.log_change(request, user, "관리자가 사용자 계정 정지를 해제했습니다.")


@admin.register(UserBlock)
class UserBlockAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("blocker", "blocked", "created_at")
    list_select_related = ("blocker", "blocked")
    raw_id_fields = ("blocker", "blocked")
    readonly_fields = ("created_at",)
    search_fields = ("blocker__username", "blocked__username")


@admin.register(LoginAttempt)
class LoginAttemptAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "scope",
        "key_hash_prefix",
        "failures",
        "window_started",
        "locked_until",
    )
    list_filter = ("scope",)
    readonly_fields = (
        "scope",
        "key_hash",
        "failures",
        "window_started",
        "locked_until",
    )

    @admin.display(description="Key hash")
    def key_hash_prefix(self, obj):
        return f"{obj.key_hash[:12]}..."

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
