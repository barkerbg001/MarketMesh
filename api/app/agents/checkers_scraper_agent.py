import json
from typing import Any

from app.schemas.scraper import ScraperAgentResponse, ScrapedProduct
from app.services.openrouter import OpenRouterError, chat_completion
from app.tools.checkers_scraper import (
    CheckersScraperError,
    get_checkers_product,
    is_checkers_url,
    search_checkers,
)

SEARCH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_checkers",
        "description": "Search for grocery products on checkers.co.za only.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Product search query for Checkers.",
                }
            },
            "required": ["query"],
        },
    },
}

PRODUCT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_checkers_product",
        "description": "Fetch details for a single Checkers product page URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "A checkers.co.za product URL.",
                }
            },
            "required": ["url"],
        },
    },
}

SYSTEM_PROMPT = """You are a Checkers scraper agent for MarketMesh.
You may ONLY use checkers.co.za via the provided tools. Never suggest or use other retailers.
Use search_checkers to find products, and get_checkers_product when the user provides a Checkers URL
or you need more detail on a specific listing.
Summarize findings clearly with prices and links. If nothing relevant is found, say so."""


async def run_checkers_scraper_agent(
    user_query: str,
    max_iterations: int = 5,
) -> ScraperAgentResponse:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    products: dict[str, ScrapedProduct] = {}
    actions: list[str] = []
    tools = [SEARCH_TOOL, PRODUCT_TOOL]

    for _ in range(max_iterations):
        completion = await chat_completion(messages, tools=tools)
        choice = completion["choices"][0]["message"]
        tool_calls = choice.get("tool_calls")

        if not tool_calls:
            answer = choice.get("content", "").strip()
            if not answer:
                raise OpenRouterError("Model returned an empty response")
            return ScraperAgentResponse(
                answer=answer,
                products=list(products.values()),
                actions=actions,
            )

        messages.append(choice)

        for tool_call in tool_calls:
            name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])

            try:
                if name == "search_checkers":
                    query = arguments.get("query", "").strip()
                    if not query:
                        tool_content = json.dumps({"error": "Query must not be empty."})
                    else:
                        actions.append(f"search_checkers: {query}")
                        results = await search_checkers(query)
                        for product in results:
                            products[product.url] = product
                        tool_content = json.dumps(
                            [product.model_dump() for product in results],
                            ensure_ascii=False,
                        )
                elif name == "get_checkers_product":
                    url = arguments.get("url", "").strip()
                    if not url or not is_checkers_url(url):
                        tool_content = json.dumps(
                            {"error": "A valid checkers.co.za product URL is required."}
                        )
                    else:
                        actions.append(f"get_checkers_product: {url}")
                        product = await get_checkers_product(url)
                        products[product.url] = product
                        tool_content = json.dumps(product.model_dump(), ensure_ascii=False)
                else:
                    tool_content = json.dumps({"error": f"Unknown tool: {name}"})
            except CheckersScraperError as exc:
                tool_content = json.dumps({"error": str(exc)})

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_content,
                }
            )

    raise OpenRouterError("Scraper agent exceeded the maximum number of tool calls")
