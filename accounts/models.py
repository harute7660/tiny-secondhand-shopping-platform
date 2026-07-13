from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.functions import Lower
from django.utils import timezone


class User(AbstractUser):
    """Application user with a canonical, case-insensitive username."""

    bio = models.CharField(max_length=500, blank=True)
    is_suspended = models.BooleanField(default=False, db_index=True)
    suspension_reason = models.CharField(max_length=500, blank=True)
    suspended_at = models.DateTimeField(null=True, blank=True)

    class Meta(AbstractUser.Meta):
        permissions = [
            ("suspend_user", "Can suspend ordinary user accounts"),
        ]
        constraints = [
            models.UniqueConstraint(
                Lower("username"),
                name="acct_user_username_ci_uniq",
            ),
            models.CheckConstraint(
                condition=models.Q(is_suspended=False) | models.Q(is_active=False),
                name="acct_user_suspended_inactive",
            ),
        ]

    @classmethod
    def normalize_username_value(cls, username):
        """Apply Django's Unicode normalization, then store lowercase only."""
        return cls.normalize_username(username or "").strip().lower()

    def clean(self):
        super().clean()
        self.username = self.normalize_username_value(self.username)
        if self.is_suspended:
            self.is_active = False

    def save(self, *args, **kwargs):
        original_username = self.username
        self.username = self.normalize_username_value(self.username)

        if self.is_suspended:
            self.is_active = False
            if self.suspended_at is None:
                self.suspended_at = timezone.now()
        else:
            self.suspended_at = None
            self.suspension_reason = ""

        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            update_fields = set(update_fields)
            if self.username != original_username:
                update_fields.add("username")
            if "is_suspended" in update_fields:
                update_fields.update({"is_active", "suspended_at", "suspension_reason"})
            kwargs["update_fields"] = update_fields

        return super().save(*args, **kwargs)


class UserBlock(models.Model):
    blocker = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blocked_users",
    )
    blocked = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="blocked_by_users",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("blocker", "blocked"),
                name="acct_userblock_pair_uniq",
            ),
            models.CheckConstraint(
                condition=~models.Q(blocker=models.F("blocked")),
                name="acct_userblock_no_self",
            ),
        ]
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.blocker_id} blocks {self.blocked_id}"


class LoginAttempt(models.Model):
    class Scope(models.TextChoices):
        ACCOUNT = "ACCOUNT", "Account"
        NETWORK = "NETWORK", "Network"

    scope = models.CharField(max_length=7, choices=Scope.choices)
    key_hash = models.CharField(max_length=64)
    failures = models.PositiveSmallIntegerField(default=0)
    window_started = models.DateTimeField(default=timezone.now)
    locked_until = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("scope", "key_hash"),
                name="acct_loginattempt_scope_key_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=("window_started",),
                name="acct_login_window_idx",
            ),
        ]

    def __str__(self):
        return f"{self.scope}:{self.key_hash[:10]}... ({self.failures})"
