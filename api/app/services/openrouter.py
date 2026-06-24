from typing import Any

import httpx

from app.core.config import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"


class OpenRouterError(Exception):
    pass


async def chat_completion(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not settings.open_router_api_key:
        raise OpenRouterError("OPEN_ROUTER_API_KEY is not configured")

    payload: dict[str, Any] = {
        "model": settings.open_router_model,
        "messages": messages,
    }
    if tools:
        payload["tools"] = tools

    headers = {
        "Authorization": f"Bearer {settings.open_router_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:5173",
        "X-Title": settings.app_name,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            f"{OPENROUTER_BASE_URL}/chat/completions",
            json=payload,
            headers=headers,
        )

    if response.status_code != 200:
        raise OpenRouterError(
            f"OpenRouter request failed ({response.status_code}): {response.text}"
        )

    return response.json()
