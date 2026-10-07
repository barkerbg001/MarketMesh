from django.urls import path

from catalog.views import ProductSearchView

urlpatterns = [
    path("products/search", ProductSearchView.as_view(), name="products-search"),
]
