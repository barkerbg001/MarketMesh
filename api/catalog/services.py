import asyncio
from collections.abc import Sequence
from dataclasses import dataclass, field

from asgiref.sync import async_to_sync

from core.types import ScrapedProduct
from retailers.errors import ScraperError
from retailers.registry import get_retailer


@dataclass
class ProductSearchOutcome:
    query: str
    products: list[ScrapedProduct] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


async def _search_retailer(
    retailer: str,
    query: str,
    max_results: int,
) -> tuple[list[ScrapedProduct], str | None]:
    try:
        products = await get_retailer(retailer).search(query, max_results=max_results)
        return products, None
    except ScraperError as exc:
        return [], str(exc)
    except Exception as exc:
        return [], f"{retailer} search failed: {exc}"


async def search_products_async(
    query: str,
    retailers: Sequence[str],
    max_results: int,
) -> ProductSearchOutcome:
    results = await asyncio.gather(
        *[_search_retailer(retailer, query, max_results) for retailer in retailers]
    )

    outcome = ProductSearchOutcome(query=query)
    for retailer, (retailer_products, error) in zip(retailers, results, strict=True):
        if error:
            outcome.errors[retailer] = error
        outcome.products.extend(retailer_products)
    return outcome


def search_products(query: str, retailers: Sequence[str], max_results: int) -> ProductSearchOutcome:
    return async_to_sync(search_products_async)(query, retailers, max_results)
