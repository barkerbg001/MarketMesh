import re
from urllib.parse import quote_plus, urljoin, urlparse

from bs4 import BeautifulSoup

from core.types import ScrapedProduct
from retailers.browser import fetch_page_html
from retailers.errors import ScraperError
from retailers.scrapers import extract_image_url

TAKEALOT_BASE = "https://www.takealot.com"
TAKEALOT_DOMAIN = "takealot.com"
PLID_PATTERN = re.compile(r"/PLID\d+")
PRICE_PATTERN = re.compile(r"R\s?[\d\s,]+(?:\.\d{2})?")


class TakealotScraperError(ScraperError):
    pass


def is_takealot_url(url: str) -> bool:
    hostname = urlparse(url).netloc.lower()
    return hostname == TAKEALOT_DOMAIN or hostname.endswith(f".{TAKEALOT_DOMAIN}")


def normalize_takealot_url(url: str) -> str:
    if url.startswith("/"):
        return urljoin(TAKEALOT_BASE, url)
    if not is_takealot_url(url):
        raise TakealotScraperError("Only takealot.com URLs are supported")
    return url


def _extract_price(text: str) -> str | None:
    matches = PRICE_PATTERN.findall(text.replace("\xa0", " "))
    if not matches:
        return None
    return max(matches, key=lambda match: len(re.sub(r"\D", "", match)))


def _parse_search_results(html: str, max_results: int) -> list[ScrapedProduct]:
    soup = BeautifulSoup(html, "lxml")
    products: list[ScrapedProduct] = []
    seen_urls: set[str] = set()

    for link in soup.select('a[href*="/PLID"]'):
        href = link.get("href")
        if not href or not PLID_PATTERN.search(href):
            continue

        url = normalize_takealot_url(href.split("?")[0])
        if url in seen_urls:
            continue

        title = link.get_text(" ", strip=True)
        container = link.find_parent(["article", "div", "li"])
        container_text = container.get_text(" ", strip=True) if container else title

        if not title or len(title) < 3:
            title_candidates = [
                element.get_text(" ", strip=True)
                for element in (container or link).select("[class*='title'], h2, h3, h4")
            ]
            title = next((candidate for candidate in title_candidates if candidate), title)

        if not title:
            continue

        products.append(
            ScrapedProduct(
                title=title,
                price=_extract_price(container_text),
                url=url,
                retailer="takealot",
                image_url=extract_image_url(container, TAKEALOT_BASE),
            )
        )
        seen_urls.add(url)

        if len(products) >= max_results:
            break

    return products


def _parse_product_page(html: str, url: str) -> ScrapedProduct:
    soup = BeautifulSoup(html, "lxml")

    title = None
    for selector in ("h1", "[class*='title']", "[data-testid*='title']"):
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
        raise TakealotScraperError("Could not extract product title")

    page_text = soup.get_text(" ", strip=True)
    price = _extract_price(page_text)

    rating = None
    for element in soup.select("[class*='rating'], [aria-label*='rating'], [class*='review']"):
        text = element.get_text(" ", strip=True)
        if text and ("star" in text.lower() or re.search(r"\d\.\d", text)):
            rating = text
            break

    in_stock = None
    lower_text = page_text.lower()
    if "out of stock" in lower_text or "sold out" in lower_text:
        in_stock = False
    elif "add to cart" in lower_text or "in stock" in lower_text:
        in_stock = True

    return ScrapedProduct(
        title=title,
        price=price,
        url=url,
        retailer="takealot",
        rating=rating,
        in_stock=in_stock,
    )


async def search_takealot(query: str, max_results: int = 8) -> list[ScrapedProduct]:
    trimmed = query.strip()
    if not trimmed:
        raise TakealotScraperError("Search query must not be empty")

    search_url = f"{TAKEALOT_BASE}/all?qsearch={quote_plus(trimmed)}"
    html = await fetch_page_html(search_url, 'a[href*="/PLID"]')
    products = _parse_search_results(html, max_results)

    if not products:
        raise TakealotScraperError(f"No Takealot products found for '{trimmed}'")

    return products


async def get_takealot_product(url: str) -> ScrapedProduct:
    product_url = normalize_takealot_url(url)
    html = await fetch_page_html(product_url, "h1")
    return _parse_product_page(html, product_url)
