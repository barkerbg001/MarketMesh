from dataclasses import dataclass
from types import ModuleType

from core.types import ScrapedProduct
from retailers.scrapers import checkers, picknpay, takealot, woolworths


@dataclass(frozen=True)
class Retailer:
    slug: str
    label: str
    domain: str
    module: ModuleType

    async def search(self, query: str, max_results: int = 8) -> list[ScrapedProduct]:
        return await getattr(self.module, f"search_{self.slug}")(query, max_results=max_results)

    async def get_product(self, url: str) -> ScrapedProduct:
        return await getattr(self.module, f"get_{self.slug}_product")(url)

    def is_retailer_url(self, url: str) -> bool:
        return getattr(self.module, f"is_{self.slug}_url")(url)


RETAILERS: dict[str, Retailer] = {
    "takealot": Retailer("takealot", "Takealot", "takealot.com", takealot),
    "checkers": Retailer("checkers", "Checkers", "checkers.co.za", checkers),
    "woolworths": Retailer("woolworths", "Woolworths", "woolworths.co.za", woolworths),
    "picknpay": Retailer("picknpay", "Pick n Pay", "pnp.co.za", picknpay),
}

RETAILER_SLUGS: tuple[str, ...] = tuple(RETAILERS)
RETAILER_CHOICES: list[tuple[str, str]] = [(slug, r.label) for slug, r in RETAILERS.items()]


def get_retailer(slug: str) -> Retailer:
    return RETAILERS[slug]
