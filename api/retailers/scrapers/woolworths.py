import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from core.types import ScrapedProduct
from retailers.browser import fetch_page_html, run_search_flow
from retailers.errors import ScraperError
from retailers.scrapers import extract_image_url

WOOLWORTHS_HOME = "https://www.woolworths.co.za/"
WOOLWORTHS_BASE = "https://www.woolworths.co.za"
WOOLWORTHS_DOMAIN = "woolworths.co.za"
PRODUCT_ID_PATTERN = re.compile(r"/A-(\d+)")
PRICE_PATTERN = re.compile(r"R\s?[\d\s,]+(?:\.\d{2})?")


class WoolworthsScraperError(ScraperError):
    pass


def is_woolworths_url(url: str) -> bool:
    hostname = urlparse(url).netloc.lower()
    return hostname == WOOLWORTHS_DOMAIN or hostname.endswith(f".{WOOLWORTHS_DOMAIN}")


def product_url_for_id(product_id: str) -> str:
    return f"{WOOLWORTHS_BASE}/prod/_/A-{product_id}"


def normalize_woolworths_url(url: str) -> str:
    if url.startswith("/"):
        return urljoin(WOOLWORTHS_BASE, url)
    if not is_woolworths_url(url):
        raise WoolworthsScraperError("Only woolworths.co.za URLs are supported")
    return url.split("?")[0]


def _extract_price(text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", text.replace("\xa0", " "))
    cleaned = re.sub(r"(R)\s*(\d)", r"\1\2", cleaned)
    cleaned = re.sub(r"(\d)\s+(\.\d{2})", r"\1\2", cleaned)
    matches = PRICE_PATTERN.findall(cleaned)
    if not matches:
        return None
    return max(matches, key=lambda match: len(re.sub(r"\D", "", match)))


def _parse_search_results(html: str, max_results: int) -> list[ScrapedProduct]:
    soup = BeautifulSoup(html, "lxml")
    products: list[ScrapedProduct] = []
    seen_ids: set[str] = set()

    for article in soup.select('article[data-testid="product-card"]'):
        product_id = article.get("data-cnstrc-item-id")
        if not product_id or product_id in seen_ids:
            continue

        title = article.get("data-cnstrc-item-name", "").strip()
        if not title:
            title = article.get_text(" ", strip=True).split("(")[0].strip()

        price_value = article.get("data-cnstrc-item-price")
        price = f"R{price_value}" if price_value else _extract_price(article.get_text(" ", strip=True))

        products.append(
            ScrapedProduct(
                title=title,
                price=price,
                url=product_url_for_id(product_id),
                retailer="woolworths",
                image_url=extract_image_url(article, product_url_for_id(product_id)),
            )
        )
        seen_ids.add(product_id)

        if len(products) >= max_results:
            break

    return products


def _parse_product_page(html: str, url: str) -> ScrapedProduct:
    soup = BeautifulSoup(html, "lxml")

    title = None
    for selector in ("h1", "[class*='product-name'], [class*='title']"):
        element = soup.select_one(selector)
        if element:
            title = element.get_text(" ", strip=True)
            if title:
                break

    if not title:
        og_title = soup.select_one('meta[property="og:title"]')
        if og_title and og_title.get("content"):
            title = og_title["content"].strip()

    if not title:
        raise WoolworthsScraperError("Could not extract product title")

    page_text = soup.get_text(" ", strip=True)
    price = _extract_price(page_text)

    in_stock = None
    lower_text = page_text.lower()
    if "out of stock" in lower_text:
        in_stock = False
    elif "add to cart" in lower_text:
        in_stock = True

    return ScrapedProduct(
        title=title,
        price=price,
        url=url,
        retailer="woolworths",
        in_stock=in_stock,
    )


async def search_woolworths(query: str, max_results: int = 8) -> list[ScrapedProduct]:
    trimmed = query.strip()
    if not trimmed:
        raise WoolworthsScraperError("Search query must not be empty")

    html = await run_search_flow(
        WOOLWORTHS_HOME,
        trimmed,
        'article[data-testid="product-card"]',
        search_selectors='input[placeholder*="Search"], input[id*="autocomplete"]',
    )
    products = _parse_search_results(html, max_results)

    if not products:
        raise WoolworthsScraperError(f"No Woolworths products found for '{trimmed}'")

    return products


async def get_woolworths_product(url: str) -> ScrapedProduct:
    product_url = normalize_woolworths_url(url)
    html = await fetch_page_html(product_url, "h1", warmup_url=WOOLWORTHS_HOME)
    return _parse_product_page(html, product_url)
