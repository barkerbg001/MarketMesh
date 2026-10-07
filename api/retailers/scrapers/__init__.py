from urllib.parse import urljoin, urlparse

from bs4 import Tag

_IMAGE_ATTRIBUTES = ("src", "data-src", "data-original", "data-lazy-src")


def extract_image_url(container: Tag | None, base_url: str) -> str | None:
    """Return the first http(s) product image inside a result card, if any."""
    if container is None:
        return None
    for image in container.select("img"):
        for attribute in _IMAGE_ATTRIBUTES:
            value = image.get(attribute)
            if not isinstance(value, str) or not value or value.startswith("data:"):
                continue
            absolute = urljoin(base_url, value.strip())
            if urlparse(absolute).scheme in ("http", "https"):
                return absolute
        srcset = image.get("srcset")
        if isinstance(srcset, str) and srcset.strip():
            first = srcset.split(",")[0].strip().split(" ")[0]
            absolute = urljoin(base_url, first)
            if urlparse(absolute).scheme in ("http", "https"):
                return absolute
    return None
