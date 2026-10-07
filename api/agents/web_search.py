from typing import Any

from ddgs import DDGS

from core.types import SearchResult


class WebSearchError(Exception):
    pass


def search_web(query: str, max_results: int = 6, region: str = "wt-wt") -> list[SearchResult]:
    """DuckDuckGo text search (via ``ddgs``). Results are untrusted snippets."""
    try:
        with DDGS() as ddgs:
            raw_results: list[dict[str, Any]] = list(
                ddgs.text(query, region=region, max_results=max_results)
            )
    except Exception as exc:  # ddgs raises several exception types for rate limits and timeouts
        raise WebSearchError(f"Web search failed: {exc.__class__.__name__}") from exc
    return [
        SearchResult(
            title=result.get("title", ""),
            url=result.get("href", ""),
            snippet=result.get("body", ""),
        )
        for result in raw_results
        if result.get("href")
    ]
