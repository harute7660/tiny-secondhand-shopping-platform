from django.conf import settings
from django.db import models


class GlobalChatMessage(models.Model):
    """Append-only public-room message; the sender is assigned by the view."""

    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="global_chat_messages",
    )
    body = models.CharField(max_length=1_000)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at", "pk")
        indexes = [
            models.Index(fields=("created_at", "id"), name="comm_chat_time_id_idx"),
        ]

    def __str__(self):
        return f"{self.sender}: {self.body[:40]}"
