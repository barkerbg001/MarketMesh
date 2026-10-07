from django.db import models

RESEARCH_REGIONS: list[tuple[str, str]] = [
    ("za-en", "South Africa"),
    ("us-en", "United States"),
    ("uk-en", "United Kingdom"),
    ("au-en", "Australia"),
    ("ca-en", "Canada"),
    ("in-en", "India"),
    ("de-de", "Germany"),
    ("wt-wt", "Worldwide"),
]

CURRENCY_CHOICES: list[tuple[str, str]] = [
    ("ZAR", "South African rand"),
    ("USD", "US dollar"),
    ("EUR", "Euro"),
    ("GBP", "British pound"),
    ("AUD", "Australian dollar"),
    ("CAD", "Canadian dollar"),
    ("INR", "Indian rupee"),
]

GENERATION_LIMITS = {
    "temperature": (0.0, 1.5),
    "max_tokens": (256, 8000),
    "max_tool_rounds": (1, 10),
    "max_delegations": (1, 5),
    "request_timeout": (10, 180),
}


class WorkspaceSettings(models.Model):
    """Settings for this single-user installation (always the row with pk=1)."""

    encrypted_api_key = models.TextField(blank=True)
    api_key_hint = models.CharField(max_length=8, blank=True)
    api_key_updated_at = models.DateTimeField(null=True, blank=True)

    default_model = models.CharField(max_length=200, blank=True)
    agent_models = models.JSONField(default=dict, blank=True)

    temperature = models.FloatField(default=0.3)
    max_tokens = models.PositiveIntegerField(default=1500)
    max_tool_rounds = models.PositiveSmallIntegerField(default=5)
    max_delegations = models.PositiveSmallIntegerField(default=3)
    request_timeout = models.PositiveSmallIntegerField(default=60)

    research_region = models.CharField(max_length=8, choices=RESEARCH_REGIONS, default="za-en")
    currency = models.CharField(max_length=3, choices=CURRENCY_CHOICES, default="ZAR")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "workspace settings"
        verbose_name_plural = "workspace settings"

    def __str__(self) -> str:
        return "Workspace settings"

    @classmethod
    def load(cls) -> "WorkspaceSettings":
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
