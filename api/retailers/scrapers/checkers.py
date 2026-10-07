import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from core.types import ScrapedProduct
from retailers.browser import fetch_page_html, run_search_flow
from retailers.errors import ScraperError
from retailers.scrapers import extract_image_url

CHECKERS_HOME = "https://www.checkers.co.za/"
CHECKERS_DOMAINS = ("checkers.co.za", "www.checkers.co.za", "products.checkers.co.za")
PRODUCT_PATH_PATTERN = re.compile(r"/p/\d+EA|/product/[^\"'\s]+?\d+EA", re.IGNORECASE)
PRICE_PATTERN = re.compile(r"R\s?[\d\s,]+(?:\.\d{2})?")


class CheckersScraperError(ScraperError):
    pass


def is_checkers_url(url: str) -> bool:
    hostname = urlparse(url).netloc.lower()
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in CHECKERS_DOMAINS)


def normalize_checkers_url(url: str) -> str:
    if url.startswith("/"):
        return urljoin(CHECKERS_HOME, url)
    if not is_checkers_url(url):
        raise CheckersScraperError("Only checkers.co.za URLs are supported")
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
    seen_urls: set[str] = set()

    for link in soup.select('a[href*="/p/"], a[href*="/product/"]'):
        href = link.get("href")
        if not href or not PRODUCT_PATH_PATTERN.search(href):
            continue

        url = normalize_checkers_url(href)
        if url in seen_urls:
            continue

        title = link.get_text(" ", strip=True)
        container = link.find_parent(["article", "div", "li"])
        container_text = container.get_text(" ", strip=True) if container else title

        if not title or len(title) < 3:
            title_candidates = [
                element.get_text(" ", strip=True)
                for element in (container or link).select(
                    "[class*='title'], [class*='name'], h2, h3, h4"
                )
            ]
            title = next((candidate for candidate in title_candidates if candidate), title)

        if not title:
            continue

        products.append(
            ScrapedProduct(
                title=title,
                price=_extract_price(container_text),
                url=url,
                retailer="checkers",
                image_url=extract_image_url(container, url),
            )
        )
        seen_urls.add(url)

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
        raise CheckersScraperError("Could not extract product title")

    page_text = soup.get_text(" ", strip=True)
    price = _extract_price(page_text)

    in_stock = None
    lower_text = page_text.lower()
    if "out of stock" in lower_text:
        in_stock = False
    elif "add to cart" in lower_text or "add to list" in lower_text:
        in_stock = True

    return ScrapedProduct(
        title=title,
        price=price,
        url=url,
        retailer="checkers",
        in_stock=in_stock,
    )


async def search_checkers(query: str, max_results: int = 8) -> list[ScrapedProduct]:
    trimmed = query.strip()
    if not trimmed:
        raise CheckersScraperError("Search query must not be empty")

    html = await run_search_flow(
        CHECKERS_HOME,
        trimmed,
        'a[href*="/p/"], a[href*="/product/"]',
    )
    products = _parse_search_results(html, max_results)

    if not products:
        raise CheckersScraperError(f"No Checkers products found for '{trimmed}'")

    return products


async def get_checkers_product(url: str) -> ScrapedProduct:
    product_url = normalize_checkers_url(url)
    html = await fetch_page_html(product_url, "h1", warmup_url=CHECKERS_HOME)
    return _parse_product_page(html, product_url)
