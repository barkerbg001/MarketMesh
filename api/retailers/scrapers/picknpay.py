import re
from urllib.parse import quote, urljoin, urlparse

from bs4 import BeautifulSoup

from app.schemas.scraper import ScrapedProduct
from app.tools.browser import fetch_page_html

PNP_HOME = "https://www.pnp.co.za/"
PNP_DOMAINS = ("pnp.co.za", "www.pnp.co.za", "picknpay.co.za", "www.picknpay.co.za")
PRODUCT_PATH_PATTERN = re.compile(r"/p/\d+_\w{2}\b", re.IGNORECASE)
PRICE_PATTERN = re.compile(r"R\s?[\d\s,]+(?:\.\d{2})?")


class PicknPayScraperError(Exception):
    pass


def is_picknpay_url(url: str) -> bool:
    hostname = urlparse(url).netloc.lower()
    return any(hostname == domain or hostname.endswith(f".{domain}") for domain in PNP_DOMAINS)


def normalize_picknpay_url(url: str) -> str:
    if url.startswith("/"):
        return urljoin(PNP_HOME, url)
    if not is_picknpay_url(url):
        raise PicknPayScraperError("Only pnp.co.za URLs are supported")
    return url.split("?")[0]


def _extract_price(text: str) -> str | None:
    cleaned = re.sub(r"\s+", " ", text.replace("\xa0", " "))
    cleaned = re.sub(r"(R)\s*(\d)", r"\1\2", cleaned)
    cleaned = re.sub(r"(\d)\s+(\.\d{2})", r"\1\2", cleaned)

    add_cart_idx = cleaned.lower().find("add to cart")
    search_text = cleaned[:add_cart_idx] if add_cart_idx != -1 else cleaned

    matches = PRICE_PATTERN.findall(search_text)
    if not matches:
        return None
    return matches[-1]


def _parse_search_results(html: str, max_results: int) -> list[ScrapedProduct]:
    soup = BeautifulSoup(html, "lxml")
    products: list[ScrapedProduct] = []
    seen_urls: set[str] = set()

    containers = soup.select(".product-grid-item")
    if not containers:
        containers = [
            link.find_parent(["article", "div", "li"])
            for link in soup.select('a[href*="/p/"]')
        ]
        containers = [container for container in containers if container is not None]

    for container in containers:
        link = container.select_one('a[href*="/p/"]')
        if not link:
            continue

        href = link.get("href")
        if not href or not PRODUCT_PATH_PATTERN.search(href):
            continue

        url = normalize_picknpay_url(href)
        if url in seen_urls:
            continue

        title = None
        for element in container.select("[class*='title'], [class*='name'], h2, h3, h4"):
            candidate = element.get_text(" ", strip=True)
            if candidate and len(candidate) > 2:
                title = candidate
                break

        if not title:
            title = link.get_text(" ", strip=True)

        if not title:
            continue

        products.append(
            ScrapedProduct(
                title=title,
                price=_extract_price(container.get_text(" ", strip=True)),
                url=url,
                retailer="picknpay",
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
        raise PicknPayScraperError("Could not extract product title")

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
        retailer="picknpay",
        in_stock=in_stock,
    )


async def search_picknpay(query: str, max_results: int = 8) -> list[ScrapedProduct]:
    trimmed = query.strip()
    if not trimmed:
        raise PicknPayScraperError("Search query must not be empty")

    search_url = f"{PNP_HOME}search/{quote(trimmed)}"
    html = await fetch_page_html(
        search_url,
        ".product-grid-item",
        warmup_url=PNP_HOME,
    )
    products = _parse_search_results(html, max_results)

    if not products:
        raise PicknPayScraperError(f"No Pick n Pay products found for '{trimmed}'")

    return products


async def get_picknpay_product(url: str) -> ScrapedProduct:
    product_url = normalize_picknpay_url(url)
    html = await fetch_page_html(product_url, "h1", warmup_url=PNP_HOME)
    return _parse_product_page(html, product_url)
