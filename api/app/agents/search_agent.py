import json
from typing import Any

from app.schemas.search import SearchAgentResponse, SearchResult
from app.services.openrouter import OpenRouterError, chat_completion
from app.tools.web_search import search_web

WEB_SEARCH_TOOL: dict[str, Any] = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "Search the web for current information on a topic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "A concise search query.",
                }
            },
            "required": ["query"],
        },
    },
}

SYSTEM_PROMPT = """You are a search agent for MarketMesh.
Use the web_search tool to find up-to-date information before answering.
Prefer multiple focused searches when a question spans several topics.
Answer clearly and concisely, and mention source URLs when relevant.
If search results are insufficient, say what is missing instead of guessing."""


async def run_search_agent(user_query: str, max_iterations: int = 4) -> SearchAgentResponse:
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_query},
    ]
    sources: dict[str, SearchResult] = {}
    queries: list[str] = []

    for _ in range(max_iterations):
        completion = await chat_completion(messages, tools=[WEB_SEARCH_TOOL])
        choice = completion["choices"][0]["message"]
        tool_calls = choice.get("tool_calls")

        if not tool_calls:
            answer = choice.get("content", "").strip()
            if not answer:
                raise OpenRouterError("Model returned an empty response")
            return SearchAgentResponse(
                answer=answer,
                sources=list(sources.values()),
                queries=queries,
            )

        messages.append(choice)

        for tool_call in tool_calls:
            if tool_call["function"]["name"] != "web_search":
                continue

            arguments = json.loads(tool_call["function"]["arguments"])
            query = arguments.get("query", "").strip()
            if not query:
                tool_content = json.dumps({"error": "Query must not be empty."})
            else:
                queries.append(query)
                results = await search_web(query)
                for result in results:
                    sources[result.url] = result
                tool_content = json.dumps(
                    [result.model_dump() for result in results],
                    ensure_ascii=False,
                )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call["id"],
                    "content": tool_content,
                }
            )

    raise OpenRouterError("Search agent exceeded the maximum number of tool calls")
