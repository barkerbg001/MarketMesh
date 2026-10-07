"""One product shape for retailer results, web-verified products, and cart items."""

import re
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from urllib.parse import urlparse, urlunparse

from django.utils import timezone

from core.types import ScrapedProduct
from retailers.registry import RETAILERS

# ISO 4217 codes the app accepts. Prices are never converted between them.
SUPPORTED_CURRENCIES: tuple[str, ...] = (
    "ZAR", "USD", "EUR", "GBP", "AUD", "CAD", "INR", "NZD", "JPY", "CHF", "SGD",
)

_NUMBER = re.compile(r"\d[\d\s,.\u00a0]*")


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    path = parsed.path.rstrip("/") or "/"
    return urlunparse((parsed.scheme.lower(), parsed.netloc.lower(), path, "", parsed.query, ""))


def source_for_url(url: str) -> str:
    host = urlparse(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def product_key(source: str, url: str) -> str:
    return f"{source.lower()}|{normalize_url(url)}"


def parse_amount(price: str | None) -> Decimal | None:
    """Parse a displayed price such as ``R1 299.00`` or ``$1,299`` into a Decimal."""
    if not price:
        return None
    match = _NUMBER.search(price.replace("\xa0", " "))
    if not match:
        return None
    raw = re.sub(r"[\s\u00a0]", "", match.group(0)).rstrip(".,")
    if "," in raw and "." in raw:
        raw = raw.replace(",", "") if raw.rfind(".") > raw.rfind(",") else raw.replace(".", "").replace(",", ".")
    elif "," in raw:
        head, _, tail = raw.rpartition(",")
        raw = f"{head.replace(',', '')}.{tail}" if len(tail) == 2 else raw.replace(",", "")
    try:
        value = Decimal(raw).quantize(Decimal("0.01"))
    except InvalidOperation:
        return None
    return value if value >= 0 else None


def iso(moment: datetime | None) -> str | None:
    return moment.isoformat() if moment else None


def from_scraped(product: ScrapedProduct, retrieved_at: datetime | None = None) -> dict[str, Any]:
    retailer = RETAILERS.get(product.retailer)
    amount = parse_amount(product.price)
    specs: dict[str, str] = {}
    if product.rating:
        specs["Rating"] = product.rating
    if product.in_stock is not None:
        specs["Availability"] = "In stock" if product.in_stock else "Out of stock"
    return {
        "key": product_key(product.retailer, product.url),
        "title": product.title,
        "url": product.url,
        "seller": retailer.label if retailer else product.retailer,
        "source": product.retailer,
        "source_type": "retailer",
        "image_url": product.image_url,
        "price": product.price,
        "price_amount": str(amount) if amount is not None else None,
        # The supported retailers are South African and list prices in rand.
        "currency": "ZAR" if amount is not None else None,
        "specs": specs,
        "retrieved_at": iso(retrieved_at or timezone.now()),
    }


def compact(product: dict[str, Any]) -> dict[str, Any]:
    """The subset of a product shown to models; keeps prompts small."""
    return {
        "key": product["key"],
        "title": product["title"],
        "seller": product.get("seller"),
        "price": product.get("price"),
        "currency": product.get("currency"),
        "specs": product.get("specs") or {},
        "url": product["url"],
        "retrieved_at": product.get("retrieved_at"),
    }
