from django.urls import path

from cart.views import CartExportView, CartImportView, CartItemView, CartView

urlpatterns = [
    path("cart", CartView.as_view(), name="cart"),
    path("cart/import", CartImportView.as_view(), name="cart-import"),
    path("cart/export", CartExportView.as_view(), name="cart-export"),
    path("cart/<int:item_id>", CartItemView.as_view(), name="cart-item"),
]
