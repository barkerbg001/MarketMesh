import json
from typing import Any

from app.schemas.scraper import ScraperAgentResponse, ScrapedProduct
from app.services.openrouter import OpenRouterError, chat_completion
from app.tools.picknpay_scraper import (
    PicknPayScraperError,
    get_picknpay_product,
    is_picknpay_url,
    search_picknpay,
)

SEARCH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "search_picknpay",
        "description": "Search for grocery products on pnp.co.za (Pick n Pay) only.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Product search query for Pick n Pay.",
                }
            },
            "required": ["query"],
        },
    },
}

PRODUCT_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "get_picknpay_product",
        "description": "Fetch details for a single Pick n Pay product page URL.",
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "A pnp.co.za product URL.",
                }
            },
            "required": ["url"],
        },
    },
}

SYSTEM_PROMPT = """You are a Pick n Pay scraper agent for MarketMesh.
You may ONLY use pnp.co.za via the provided tools. Never suggest or use other retailers.
Use search_picknpay to find products, and get_picknpay_product when the user provides a Pick n Pay URL
or you need more detail on a specific listing.
Summarize findings clearly with prices and links. If nothing relevant is found, say so."""


async def run_picknpay_scraper_agent(
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
                if name == "search_picknpay":
                    query = arguments.get("query", "").strip()
                    if not query:
                        tool_content = json.dumps({"error": "Query must not be empty."})
                    else:
                        actions.append(f"search_picknpay: {query}")
                        results = await search_picknpay(query)
                        for product in results:
                            products[product.url] = product
                        tool_content = json.dumps(
                            [product.model_dump() for product in results],
                            ensure_ascii=False,
                        )
                elif name == "get_picknpay_product":
                    url = arguments.get("url", "").strip()
                    if not url or not is_picknpay_url(url):
                        tool_content = json.dumps(
                            {"error": "A valid pnp.co.za product URL is required."}
                        )
                    else:
                        actions.append(f"get_picknpay_product: {url}")
                        product = await get_picknpay_product(url)
                        products[product.url] = product
                        tool_content = json.dumps(product.model_dump(), ensure_ascii=False)
                else:
                    tool_content = json.dumps({"error": f"Unknown tool: {name}"})
            except PicknPayScraperError as exc:
                tool_content = json.dumps({"error": str(exc)})

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_content,
                }
            )

    raise OpenRouterError("Scraper agent exceeded the maximum number of tool calls")
