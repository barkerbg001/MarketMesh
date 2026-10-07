import uuid

from django.db import models


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, default="New research")
    research_context = models.JSONField(
        default=dict,
        blank=True,
        help_text="Products and sources retrieved in this conversation, shared by all agents.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return self.title


class Message(models.Model):
    class Role(models.TextChoices):
        USER = "user", "User"
        ASSISTANT = "assistant", "Agent"

    class Status(models.TextChoices):
        COMPLETE = "complete", "Complete"
        STREAMING = "streaming", "Streaming"
        CANCELLED = "cancelled", "Cancelled"
        ERROR = "error", "Error"

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=16, choices=Role.choices)
    agent = models.CharField(max_length=32, blank=True)
    content = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.COMPLETE)
    payload = models.JSONField(
        default=dict,
        blank=True,
        help_text="Products, sources, comparison, tool activity, delegation, and errors.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at", "id"]
        indexes = [models.Index(fields=["conversation", "created_at"], name="research_msg_conv_created")]

    def __str__(self) -> str:
        who = self.agent or self.role
        return f"{who}: {self.content[:60]}"
