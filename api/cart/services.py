import csv
import io
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils.dateparse import parse_datetime

from cart.models import CartItem
from catalog.products import (
    SUPPORTED_CURRENCIES,
    iso,
    parse_amount,
    product_key,
    source_for_url,
)
from retailers.registry import RETAILERS

MAX_QUANTITY = 99


@dataclass
class AddResult:
    item: CartItem
    created: bool
    duplicate: bool


def _amount_and_currency(product: dict[str, Any]) -> tuple[Decimal | None, str]:
    currency = (product.get("currency") or "").upper()
    if currency not in SUPPORTED_CURRENCIES:
        return None, ""
    amount = parse_amount(str(product.get("price_amount") or "")) or parse_amount(product.get("price"))
    return (amount, currency) if amount is not None else (None, "")


def add_product(
    product: dict[str, Any],
    *,
    quantity: int = 1,
    increment: bool = False,
    conversation_id: Any = None,
) -> AddResult:
    """Add a product, or report it as a duplicate.

    An existing item is left unchanged unless ``increment`` is true, in which
    case its quantity grows by ``quantity`` (capped at ``MAX_QUANTITY``).
    """
    url = product["url"]
    source = product.get("source") or source_for_url(url)
    key = product_key(source, url)
    quantity = max(1, min(int(quantity), MAX_QUANTITY))

    with transaction.atomic():
        existing = CartItem.objects.select_for_update().filter(product_key=key).first()
        if existing:
            if increment:
                existing.quantity = min(existing.quantity + quantity, MAX_QUANTITY)
                existing.save(update_fields=["quantity", "updated_at"])
            return AddResult(existing, created=False, duplicate=True)

        amount, currency = _amount_and_currency(product)
        retrieved = product.get("retrieved_at")
        seller = product.get("seller") or (RETAILERS[source].label if source in RETAILERS else source)
        item = CartItem.objects.create(
            product_key=key,
            title=str(product["title"])[:500],
            url=url,
            seller=str(seller)[:200],
            source=source[:200],
            image_url=product.get("image_url") or "",
            price_text=str(product.get("price") or "")[:64],
            price_amount=amount,
            currency=currency,
            specs={str(k)[:80]: str(v)[:300] for k, v in (product.get("specs") or {}).items()},
            quantity=quantity,
            retrieved_at=parse_datetime(retrieved) if isinstance(retrieved, str) else None,
            conversation_id=conversation_id,
        )
    return AddResult(item, created=True, duplicate=False)


def serialize_item(item: CartItem) -> dict[str, Any]:
    line_total = item.price_amount * item.quantity if item.price_amount is not None and item.currency else None
    return {
        "id": item.id,
        "product_key": item.product_key,
        "title": item.title,
        "url": item.url,
        "seller": item.seller,
        "source": item.source,
        "image_url": item.image_url or None,
        "price": item.price_text or None,
        "price_amount": str(item.price_amount) if item.price_amount is not None else None,
        "currency": item.currency or None,
        "line_total": str(line_total) if line_total is not None else None,
        "specs": item.specs or {},
        "notes": item.notes,
        "quantity": item.quantity,
        "retrieved_at": iso(item.retrieved_at),
        "conversation_id": str(item.conversation_id) if item.conversation_id else None,
        "added_at": iso(item.added_at),
    }


def summarize(items: list[CartItem]) -> dict[str, Any]:
    """Subtotals per currency. Items without a known price and currency are counted, never summed."""
    totals: dict[str, Decimal] = defaultdict(Decimal)
    counts: dict[str, int] = defaultdict(int)
    unknown = 0
    for item in items:
        if item.price_amount is None or not item.currency:
            unknown += item.quantity
            continue
        totals[item.currency] += item.price_amount * item.quantity
        counts[item.currency] += item.quantity
    return {
        "subtotals": [
            {"currency": currency, "amount": str(totals[currency]), "item_count": counts[currency]}
            for currency in sorted(totals)
        ],
        "unknown_price_count": unknown,
        "item_count": sum(item.quantity for item in items),
    }


def cart_payload() -> dict[str, Any]:
    items = list(CartItem.objects.all())
    return {"items": [serialize_item(item) for item in items], **summarize(items)}


def as_product(item: CartItem) -> dict[str, Any]:
    """A cart item in the shared product shape, for agents."""
    return {
        "key": item.product_key,
        "title": item.title,
        "url": item.url,
        "seller": item.seller,
        "source": item.source,
        "source_type": "retailer" if item.source in RETAILERS else "web",
        "image_url": item.image_url or None,
        "price": item.price_text or None,
        "price_amount": str(item.price_amount) if item.price_amount is not None else None,
        "currency": item.currency or None,
        "specs": item.specs or {},
        "retrieved_at": iso(item.retrieved_at),
        "notes": item.notes,
        "quantity": item.quantity,
    }


EXPORT_COLUMNS = (
    "title", "seller", "price", "currency", "quantity", "line_total", "url", "retrieved_at", "notes",
)


def export_csv(items: list[CartItem]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(EXPORT_COLUMNS)
    for item in items:
        row = serialize_item(item)
        writer.writerow([row[column] if row[column] is not None else "" for column in EXPORT_COLUMNS])
    return buffer.getvalue()


def import_legacy(entries: list[dict[str, Any]]) -> int:
    """Import the pre-chat browser cart (``localStorage['marketmesh-cart']``)."""
    imported = 0
    for entry in entries:
        retailer = entry.get("retailer") or ""
        price = entry.get("price")
        amount = parse_amount(price)
        result = add_product(
            {
                "title": entry["title"],
                "url": entry["url"],
                "source": retailer or source_for_url(entry["url"]),
                "seller": RETAILERS[retailer].label if retailer in RETAILERS else None,
                "price": price,
                "price_amount": str(amount) if amount is not None else None,
                "currency": "ZAR" if amount is not None and retailer in RETAILERS else None,
                "specs": {},
            },
            quantity=int(entry.get("quantity") or 1),
            increment=True,
        )
        imported += 1 if result.created or result.duplicate else 0
    return imported
