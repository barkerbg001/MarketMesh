from django.db import models

from retailers.registry import RETAILER_CHOICES


class SearchRun(models.Model):
    class Kind(models.TextChoices):
        PRODUCT_SEARCH = "product_search", "Product search"
        AGENT_SEARCH = "agent_search", "Web search agent"
        AGENT_SCRAPE = "agent_scrape", "Scraper agent"

    class Status(models.TextChoices):
        SUCCESS = "success", "Success"
        PARTIAL = "partial", "Partial (some retailers failed)"
        FAILED = "failed", "Failed"

    kind = models.CharField(max_length=32, choices=Kind.choices)
    retailer = models.CharField(
        max_length=32,
        choices=RETAILER_CHOICES,
        blank=True,
        help_text="Retailer for scraper-agent runs; blank for multi-retailer or web searches.",
    )
    query = models.TextField()
    retailers = models.JSONField(default=list, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices)
    http_status = models.PositiveSmallIntegerField()
    result_count = models.PositiveIntegerField(default=0)
    answer = models.TextField(blank=True)
    errors = models.JSONField(default=dict, blank=True)
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Agent metadata such as web-search queries, sources, or scraper actions.",
    )
    duration_ms = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["kind", "-created_at"], name="history_run_kind_created"),
            models.Index(fields=["status", "-created_at"], name="history_run_status_created"),
        ]

    def __str__(self) -> str:
        return f"{self.get_kind_display()}: {self.query[:60]}"


class SearchRunProduct(models.Model):
    run = models.ForeignKey(SearchRun, on_delete=models.CASCADE, related_name="products")
    position = models.PositiveIntegerField()
    retailer = models.CharField(max_length=32, db_index=True)
    title = models.TextField()
    price = models.CharField(max_length=64, null=True, blank=True)
    url = models.URLField(max_length=2000)
    rating = models.CharField(max_length=255, null=True, blank=True)
    in_stock = models.BooleanField(null=True)

    class Meta:
        ordering = ["run", "position"]
        constraints = [
            models.UniqueConstraint(fields=["run", "position"], name="history_product_run_position"),
        ]

    def __str__(self) -> str:
        return self.title[:80]
