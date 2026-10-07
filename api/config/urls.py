from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularJSONAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from core.views import RootView

admin.site.site_header = "MarketMesh admin"
admin.site.site_title = "MarketMesh admin"
admin.site.index_title = "Research data"

urlpatterns = [
    path("", RootView.as_view(), name="root"),
    path("admin/", admin.site.urls),
    path("openapi.json", SpectacularJSONAPIView.as_view(), name="openapi-schema"),
    path("docs", SpectacularSwaggerView.as_view(url_name="openapi-schema"), name="swagger-ui"),
    path("redoc", SpectacularRedocView.as_view(url_name="openapi-schema"), name="redoc"),
    path("api/", include("core.urls")),
    path("api/", include("catalog.urls")),
    path("api/", include("research.urls")),
    path("api/", include("cart.urls")),
    path("api/", include("workspace.urls")),
]
