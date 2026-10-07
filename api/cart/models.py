from django.db import models


class CartItem(models.Model):
    """A shortlisted product. The cart is a research list: nothing is reserved or bought."""

    product_key = models.CharField(max_length=700, unique=True)
    title = models.CharField(max_length=500)
    url = models.URLField(max_length=2000)
    seller = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=200, blank=True)
    image_url = models.URLField(max_length=2000, blank=True)
    price_text = models.CharField(max_length=64, blank=True)
    price_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    currency = models.CharField(max_length=3, blank=True)
    specs = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, max_length=1000)
    quantity = models.PositiveIntegerField(default=1)
    retrieved_at = models.DateTimeField(null=True, blank=True)
    conversation = models.ForeignKey(
        "research.Conversation",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="cart_items",
    )
    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["added_at", "id"]

    def __str__(self) -> str:
        return self.title[:80]
