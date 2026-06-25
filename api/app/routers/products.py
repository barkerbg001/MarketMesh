import asyncio
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.schemas.scraper import ScrapedProduct
from app.tools.checkers_scraper import CheckersScraperError, search_checkers
from app.tools.picknpay_scraper import PicknPayScraperError, search_picknpay
from app.tools.takealot_scraper import TakealotScraperError, search_takealot
from app.tools.woolworths_scraper import WoolworthsScraperError, search_woolworths

router = APIRouter(prefix="/products", tags=["products"])

Retailer = Literal["takealot", "checkers", "woolworths", "picknpay"]
ALL_RETAILERS: tuple[Retailer, ...] = ("takealot", "checkers", "woolworths", "picknpay")

RETAILER_SEARCH = {
    "takealot": search_takealot,
    "checkers": search_checkers,
    "woolworths": search_woolworths,
    "picknpay": search_picknpay,
}


class ProductSearchRequest(BaseModel):
    query: str = Field(min_length=1, max_length=200)
    retailers: list[Retailer] = Field(default_factory=lambda: list(ALL_RETAILERS))
    max_results: int = Field(default=12, ge=1, le=24)


class ProductSearchResponse(BaseModel):
    query: str
    products: list[ScrapedProduct]
    errors: dict[str, str] = Field(default_factory=dict)


async def _search_retailer(
    retailer: Retailer,
    query: str,
    max_results: int,
) -> tuple[list[ScrapedProduct], str | None]:
    try:
        products = await RETAILER_SEARCH[retailer](query, max_results=max_results)
        return products, None
    except (TakealotScraperError, CheckersScraperError, WoolworthsScraperError, PicknPayScraperError) as exc:
        return [], str(exc)
    except Exception as exc:
        return [], f"{retailer} search failed: {exc}"


@router.post("/search", response_model=ProductSearchResponse)
async def search_products(request: ProductSearchRequest) -> ProductSearchResponse:
    retailers = request.retailers or list(ALL_RETAILERS)
    if not retailers:
        raise HTTPException(status_code=400, detail="At least one retailer is required")

    trimmed = request.query.strip()
    if not trimmed:
        raise HTTPException(status_code=400, detail="Search query must not be empty")

    results = await asyncio.gather(
        *[
            _search_retailer(retailer, trimmed, request.max_results)
            for retailer in retailers
        ]
    )

    products: list[ScrapedProduct] = []
    errors: dict[str, str] = {}

    for retailer, (retailer_products, error) in zip(retailers, results, strict=True):
        if error:
            errors[retailer] = error
        products.extend(retailer_products)

    if not products and errors:
        raise HTTPException(
            status_code=502,
            detail={"message": "No products found", "errors": errors},
        )

    return ProductSearchResponse(query=trimmed, products=products, errors=errors)
