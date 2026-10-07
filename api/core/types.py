from dataclasses import asdict, dataclass
from typing import Any


@dataclass(slots=True)
class ScrapedProduct:
    title: str
    url: str
    retailer: str
    price: str | None = None
    rating: str | None = None
    in_stock: bool | None = None
    image_url: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "price": self.price,
            "url": self.url,
            "retailer": self.retailer,
            "rating": self.rating,
            "in_stock": self.in_stock,
            "image_url": self.image_url,
        }


@dataclass(slots=True)
class SearchResult:
    title: str
    url: str
    snippet: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
