from django.contrib import admin

from cart.models import CartItem


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("title", "seller", "price_text", "currency", "quantity", "added_at")
    search_fields = ("title", "seller", "url")
    list_filter = ("currency",)
