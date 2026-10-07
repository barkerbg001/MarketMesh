from django.contrib import admin
from django.http import HttpRequest
from django.utils.html import format_html

from history.models import SearchRun, SearchRunProduct


class ReadOnlyAdminMixin:
    """History is an audit log: viewable and deletable, never hand-edited."""

    def has_add_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object = None) -> bool:
        return False


class SearchRunProductInline(ReadOnlyAdminMixin, admin.TabularInline):
    model = SearchRunProduct
    extra = 0
    can_delete = False
    fields = ("position", "retailer", "title", "price", "rating", "in_stock", "product_link")
    readonly_fields = fields
    ordering = ("position",)

    @admin.display(description="URL")
    def product_link(self, obj: SearchRunProduct) -> str:
        return format_html('<a href="{}" target="_blank" rel="noreferrer">Open</a>', obj.url)


@admin.register(SearchRun)
class SearchRunAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = (
        "created_at",
        "kind",
        "retailer",
        "short_query",
        "status",
        "http_status",
        "result_count",
        "duration_ms",
    )
    list_filter = ("kind", "status", "retailer", "created_at")
    search_fields = ("query", "answer")
    date_hierarchy = "created_at"
    readonly_fields = (
        "kind",
        "retailer",
        "query",
        "retailers",
        "status",
        "http_status",
        "result_count",
        "answer",
        "errors",
        "details",
        "duration_ms",
        "created_at",
    )
    inlines = (SearchRunProductInline,)
    list_per_page = 50

    @admin.display(description="Query", ordering="query")
    def short_query(self, obj: SearchRun) -> str:
        return obj.query if len(obj.query) <= 80 else f"{obj.query[:77]}..."


@admin.register(SearchRunProduct)
class SearchRunProductAdmin(ReadOnlyAdminMixin, admin.ModelAdmin):
    list_display = ("title", "retailer", "price", "in_stock", "run")
    list_filter = ("retailer", "in_stock")
    search_fields = ("title", "url")
    list_select_related = ("run",)
    readonly_fields = ("run", "position", "retailer", "title", "price", "url", "rating", "in_stock")
    list_per_page = 50
