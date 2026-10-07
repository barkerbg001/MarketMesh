"""Fetch a public web page for the agents, as untrusted text.

Only public http(s) hosts are allowed (no loopback, private, link-local, or
reserved addresses), redirects are re-checked, and the body size is capped.
"""

import ipaddress
import json
import re
import socket
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

MAX_BYTES = 1_500_000
MAX_REDIRECTS = 3
MAX_TEXT = 60_000
USER_AGENT = "Mozilla/5.0 (compatible; MarketMeshResearch/1.0; +https://github.com/)"
_ALLOWED_TYPES = ("text/html", "application/xhtml+xml", "text/plain")


class PageFetchError(Exception):
    pass


@dataclass
class PageContent:
    url: str
    title: str
    text: str
    description: str = ""
    image_url: str | None = None
    structured_products: list[dict[str, Any]] = field(default_factory=list)


def _check_public_host(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise PageFetchError("Only public http(s) URLs can be fetched.")
    if parsed.port not in (None, 80, 443):
        raise PageFetchError("Only standard web ports (80/443) can be fetched.")
    try:
        infos = socket.getaddrinfo(parsed.hostname, parsed.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise PageFetchError(f"Could not resolve {parsed.hostname}.") from exc
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global or address.is_multicast:
            raise PageFetchError("That address is not a public website and was not fetched.")


def _walk_json_ld(node: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(node, list):
        for item in node:
            found.extend(_walk_json_ld(item))
    elif isinstance(node, dict):
        kind = node.get("@type")
        kinds = kind if isinstance(kind, list) else [kind]
        if "Product" in kinds:
            found.append(node)
        for key in ("@graph", "itemListElement", "item", "mainEntity"):
            if key in node:
                found.extend(_walk_json_ld(node[key]))
    return found


def _first(value: Any) -> Any:
    return value[0] if isinstance(value, list) and value else value


def _structured_products(soup: BeautifulSoup) -> list[dict[str, Any]]:
    products = []
    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except ValueError:
            continue
        for node in _walk_json_ld(data):
            offers = _first(node.get("offers")) or {}
            if isinstance(offers, dict) and offers.get("@type") == "AggregateOffer":
                price = offers.get("lowPrice")
            else:
                price = offers.get("price") if isinstance(offers, dict) else None
            brand = _first(node.get("brand"))
            image = _first(node.get("image"))
            products.append(
                {
                    "name": str(node.get("name") or "")[:300],
                    "price": str(price) if price not in (None, "") else None,
                    "currency": (offers.get("priceCurrency") if isinstance(offers, dict) else None),
                    "availability": str(offers.get("availability") or "").rsplit("/", 1)[-1]
                    if isinstance(offers, dict)
                    else "",
                    "brand": brand.get("name") if isinstance(brand, dict) else (brand or None),
                    "image": image.get("url") if isinstance(image, dict) else image,
                }
            )
    return products[:10]


def parse_html(html: str, url: str) -> PageContent:
    soup = BeautifulSoup(html, "lxml")
    structured = _structured_products(soup)
    title = (soup.title.string or "").strip() if soup.title and soup.title.string else ""
    description_tag = soup.select_one('meta[name="description"], meta[property="og:description"]')
    description = (description_tag.get("content") or "").strip() if description_tag else ""
    image_tag = soup.select_one('meta[property="og:image"]')
    image_url = None
    if image_tag and image_tag.get("content"):
        candidate = urljoin(url, image_tag["content"].strip())
        image_url = candidate if urlparse(candidate).scheme in ("http", "https") else None
    for tag in soup(["script", "style", "noscript", "svg", "iframe", "template", "form"]):
        tag.decompose()
    text = re.sub(r"\s+", " ", soup.get_text(" ", strip=True))[:MAX_TEXT]
    return PageContent(
        url=url,
        title=title[:300],
        text=text,
        description=description[:500],
        image_url=image_url,
        structured_products=structured,
    )


def fetch_page(url: str, *, timeout: float = 15.0) -> PageContent:
    current = url
    with httpx.Client(timeout=timeout, follow_redirects=False, headers={"User-Agent": USER_AGENT}) as client:
        for _ in range(MAX_REDIRECTS + 1):
            _check_public_host(current)
            try:
                with client.stream("GET", current) as response:
                    if response.is_redirect:
                        location = response.headers.get("location")
                        if not location:
                            raise PageFetchError("The page redirected without a destination.")
                        current = urljoin(current, location)
                        continue
                    if response.status_code >= 400:
                        raise PageFetchError(f"The page returned HTTP {response.status_code}.")
                    content_type = response.headers.get("content-type", "").split(";")[0].strip().lower()
                    if content_type and content_type not in _ALLOWED_TYPES:
                        raise PageFetchError(f"Unsupported content type: {content_type}.")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            break
                    encoding = response.encoding or "utf-8"
                    html = bytes(body).decode(encoding, errors="replace")
            except httpx.TimeoutException as exc:
                raise PageFetchError("The page took too long to respond.") from exc
            except httpx.HTTPError as exc:
                raise PageFetchError("The page could not be downloaded.") from exc
            if content_type == "text/plain":
                return PageContent(url=current, title="", text=re.sub(r"\s+", " ", html)[:MAX_TEXT])
            return parse_html(html, current)
    raise PageFetchError("Too many redirects.")
