import asyncio
from typing import Any

from ddgs import DDGS

from app.schemas.search import SearchResult


def _search_web_sync(query: str, max_results: int) -> list[dict[str, Any]]:
    with DDGS() as ddgs:
        return list(ddgs.text(query, max_results=max_results))


async def search_web(query: str, max_results: int = 5) -> list[SearchResult]:
    raw_results = await asyncio.to_thread(_search_web_sync, query, max_results)
    return [
        SearchResult(
            title=result.get("title", ""),
            url=result.get("href", ""),
            snippet=result.get("body", ""),
        )
        for result in raw_results
        if result.get("href")
    ]
