"""OpenRouter API client (https://openrouter.ai/docs).

All calls stay on the server. The API key is only ever placed in the
Authorization header; it is never logged, echoed in errors, or returned.
"""

import json
import threading
import time
from collections.abc import Callable
from typing import Any

import httpx
from django.conf import settings

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
MODELS_CACHE_SECONDS = 600
_ERROR_DETAIL_LIMIT = 300


class OpenRouterError(Exception):
    """A provider failure with a stable ``code`` the UI can act on."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "provider_error",
        status: int | None = None,
        retry_after: int | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.status = status
        self.retry_after = retry_after

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"code": self.code, "message": str(self)}
        if self.retry_after:
            data["retry_after"] = self.retry_after
        return data


class StreamCancelled(Exception):
    pass


def _headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.OPEN_ROUTER_REFERER,
        "X-Title": "MarketMesh",
    }


def _provider_message(body: Any) -> str:
    if isinstance(body, dict):
        error = body.get("error")
        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])[:_ERROR_DETAIL_LIMIT]
    return ""


def _retry_after(headers: httpx.Headers) -> int | None:
    value = headers.get("retry-after")
    try:
        return max(int(float(value)), 1) if value else None
    except ValueError:
        return None


def error_from_status(
    status: int,
    body: Any = None,
    *,
    model: str | None = None,
    retry_after: int | None = None,
) -> OpenRouterError:
    detail = _provider_message(body)
    suffix = f" OpenRouter said: {detail}" if detail else ""

    if status == 401:
        return OpenRouterError(
            "OpenRouter rejected the API key. Check it or save a new one in Settings.",
            code="invalid_key",
            status=status,
        )
    if status == 402:
        return OpenRouterError(
            "OpenRouter reports insufficient credits for this key or account. "
            "Add credits, raise the key's limit, or pick a free model in Settings." + suffix,
            code="insufficient_credits",
            status=status,
            retry_after=retry_after,
        )
    if status == 403:
        return OpenRouterError(
            "OpenRouter blocked this request (moderation, guardrail, or key permissions)." + suffix,
            code="forbidden",
            status=status,
        )
    if status == 408:
        return OpenRouterError(
            "OpenRouter timed out. Try again, or lower the response length in Settings.",
            code="timeout",
            status=status,
        )
    if status == 429:
        wait = f" Retry in about {retry_after} seconds." if retry_after else " Wait a moment and retry."
        return OpenRouterError(
            "OpenRouter rate limit reached. Free models have per-minute and daily caps." + wait,
            code="rate_limited",
            status=status,
            retry_after=retry_after,
        )
    model_problem = status == 404 or (
        status == 400 and "model" in detail.lower() and ("valid" in detail.lower() or "exist" in detail.lower())
    )
    if model_problem:
        name = f"'{model}' " if model else ""
        return OpenRouterError(
            f"The model {name}is not available on OpenRouter. Choose another model in Settings." + suffix,
            code="model_unavailable",
            status=status,
        )
    if status in (502, 503):
        return OpenRouterError(
            "The selected model's provider is unavailable right now. "
            "Try again shortly or choose another model in Settings." + suffix,
            code="model_unavailable",
            status=status,
            retry_after=retry_after,
        )
    if status == 400:
        return OpenRouterError(
            "OpenRouter rejected the request as invalid." + suffix,
            code="bad_request",
            status=status,
        )
    return OpenRouterError(
        f"OpenRouter returned an unexpected error (HTTP {status})." + suffix,
        code="provider_error",
        status=status,
    )


def _network_error(exc: httpx.HTTPError) -> OpenRouterError:
    if isinstance(exc, httpx.TimeoutException):
        return OpenRouterError(
            "Timed out waiting for OpenRouter. Try again, or raise the request timeout in Settings.",
            code="timeout",
        )
    return OpenRouterError(
        "Could not reach OpenRouter. Check the server's internet connection.",
        code="network_error",
    )


def _require_key(api_key: str | None) -> str:
    if not api_key:
        raise OpenRouterError(
            "No OpenRouter API key is configured. Add one on the Settings page.",
            code="missing_key",
        )
    return api_key


def check_key(api_key: str | None, *, timeout: float = 15.0) -> dict[str, Any]:
    """Validate a key with ``GET /key`` and return non-sensitive usage details."""
    key = _require_key(api_key)
    try:
        response = httpx.get(f"{OPENROUTER_BASE_URL}/key", headers=_headers(key), timeout=timeout)
    except httpx.HTTPError as exc:
        raise _network_error(exc) from None
    body = _json_or_none(response)
    if response.status_code != 200:
        raise error_from_status(response.status_code, body, retry_after=_retry_after(response.headers))
    data = (body or {}).get("data") or {}
    # The key's label can contain a fragment of the key, so it is deliberately omitted.
    return {
        "is_free_tier": data.get("is_free_tier"),
        "limit": data.get("limit"),
        "limit_remaining": data.get("limit_remaining"),
        "usage": data.get("usage"),
    }


_models_cache: dict[str, Any] = {"at": 0.0, "models": None}
_models_lock = threading.Lock()


def list_models(*, timeout: float = 20.0, refresh: bool = False) -> list[dict[str, Any]]:
    """Text models that support tool calling, which every MarketMesh agent needs."""
    with _models_lock:
        cached = _models_cache["models"]
        if cached is not None and not refresh and time.monotonic() - _models_cache["at"] < MODELS_CACHE_SECONDS:
            return cached
    try:
        response = httpx.get(
            f"{OPENROUTER_BASE_URL}/models",
            params={"supported_parameters": "tools"},
            timeout=timeout,
        )
    except httpx.HTTPError as exc:
        raise _network_error(exc) from None
    body = _json_or_none(response)
    if response.status_code != 200:
        raise error_from_status(response.status_code, body)

    models = []
    for item in (body or {}).get("data") or []:
        if not isinstance(item, dict) or not item.get("id"):
            continue
        pricing = item.get("pricing") or {}
        prompt = str(pricing.get("prompt", ""))
        completion = str(pricing.get("completion", ""))
        models.append(
            {
                "id": item["id"],
                "name": item.get("name") or item["id"],
                "context_length": item.get("context_length"),
                "prompt_price": prompt or None,
                "completion_price": completion or None,
                "is_free": _is_zero(prompt) and _is_zero(completion),
            }
        )
    models.sort(key=lambda model: model["name"].lower())
    with _models_lock:
        _models_cache.update(at=time.monotonic(), models=models)
    return models


def _is_zero(value: str) -> bool:
    try:
        return float(value) == 0.0
    except ValueError:
        return False


def _json_or_none(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def stream_chat(
    messages: list[dict[str, Any]],
    *,
    api_key: str | None,
    model: str,
    tools: list[dict[str, Any]] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    timeout: float = 60.0,
    on_delta: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> dict[str, Any]:
    """Stream ``/chat/completions`` and return the assembled assistant message.

    Text deltas are passed to ``on_delta`` as they arrive. Tool-call fragments
    are accumulated by index. Returns ``{"message": {...}, "finish_reason": str}``.
    """
    key = _require_key(api_key)
    if not model:
        raise OpenRouterError(
            "No model is selected. Choose a default model on the Settings page.",
            code="missing_model",
        )

    payload: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
    if tools:
        payload["tools"] = tools
    if temperature is not None:
        payload["temperature"] = temperature
    if max_tokens is not None:
        payload["max_tokens"] = max_tokens

    content_parts: list[str] = []
    tool_calls: dict[int, dict[str, Any]] = {}
    finish_reason = "stop"

    try:
        with httpx.Client(timeout=httpx.Timeout(timeout, connect=15.0)) as client:
            with client.stream(
                "POST", f"{OPENROUTER_BASE_URL}/chat/completions", json=payload, headers=_headers(key)
            ) as response:
                if response.status_code != 200:
                    response.read()
                    raise error_from_status(
                        response.status_code,
                        _json_or_none(response),
                        model=model,
                        retry_after=_retry_after(response.headers),
                    )
                for line in response.iter_lines():
                    if should_cancel and should_cancel():
                        raise StreamCancelled()
                    if not line or line.startswith(":") or not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                    except ValueError:
                        continue
                    if isinstance(chunk.get("error"), dict):
                        code = chunk["error"].get("code")
                        raise error_from_status(
                            code if isinstance(code, int) else 502, chunk, model=model
                        )
                    choices = chunk.get("choices") or []
                    if not choices:
                        continue
                    choice = choices[0]
                    delta = choice.get("delta") or {}
                    text = delta.get("content")
                    if text:
                        content_parts.append(text)
                        if on_delta:
                            on_delta(text)
                    for fragment in delta.get("tool_calls") or []:
                        index = fragment.get("index", 0)
                        call = tool_calls.setdefault(
                            index,
                            {"id": "", "type": "function", "function": {"name": "", "arguments": ""}},
                        )
                        if fragment.get("id"):
                            call["id"] = fragment["id"]
                        function = fragment.get("function") or {}
                        if function.get("name"):
                            call["function"]["name"] += function["name"]
                        if function.get("arguments"):
                            call["function"]["arguments"] += function["arguments"]
                    if choice.get("finish_reason"):
                        finish_reason = choice["finish_reason"]
    except httpx.HTTPError as exc:
        raise _network_error(exc) from None

    if finish_reason == "error":
        raise OpenRouterError("The model stopped with an error mid-response. Try again.", code="provider_error")

    message: dict[str, Any] = {"role": "assistant", "content": "".join(content_parts)}
    ordered_calls = [tool_calls[index] for index in sorted(tool_calls)]
    for position, call in enumerate(ordered_calls):
        if not call["id"]:
            call["id"] = f"call_{position}"
    if ordered_calls:
        message["tool_calls"] = ordered_calls
    return {"message": message, "finish_reason": finish_reason}
