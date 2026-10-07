import logging
from collections.abc import Sequence
from typing import Any

from django.conf import settings
from django.db import DatabaseError, transaction

from core.types import ScrapedProduct
from history.models import SearchRun, SearchRunProduct

logger = logging.getLogger(__name__)


def record_run(
    *,
    kind: str,
    query: str,
    http_status: int,
    duration_ms: int,
    retailer: str = "",
    retailers: Sequence[str] = (),
    products: Sequence[ScrapedProduct] = (),
    errors: dict[str, str] | None = None,
    answer: str = "",
    details: dict[str, Any] | None = None,
) -> SearchRun | None:
    """Persist a search/scrape run. Never raises: history must not break the API."""
    if not settings.SEARCH_HISTORY_ENABLED:
        return None

    errors = errors or {}
    if http_status >= 400:
        status = SearchRun.Status.FAILED
    elif errors:
        status = SearchRun.Status.PARTIAL
    else:
        status = SearchRun.Status.SUCCESS

    try:
        with transaction.atomic():
            run = SearchRun.objects.create(
                kind=kind,
                retailer=retailer,
                query=query,
                retailers=list(retailers),
                status=status,
                http_status=http_status,
                result_count=len(products),
                answer=answer,
                errors=errors,
                details=details or {},
                duration_ms=max(duration_ms, 0),
            )
            SearchRunProduct.objects.bulk_create(
                SearchRunProduct(
                    run=run,
                    position=index,
                    retailer=product.retailer,
                    title=product.title,
                    price=product.price,
                    url=product.url,
                    rating=product.rating,
                    in_stock=product.in_stock,
                )
                for index, product in enumerate(products)
            )
        return run
    except DatabaseError:
        logger.exception("Failed to record %s run for query %r", kind, query)
        return None
