"""Helpers for tests that drive chat turns without calling OpenRouter."""

import json
from collections.abc import Callable
from typing import Any

from workspace.models import WorkspaceSettings
from workspace.services import save_api_key

TEST_API_KEY = "fake-openrouter-key-for-agent-tests-abcd"
TEST_MODEL = "test-vendor/test-model"

Step = str | list[tuple[str, dict[str, Any]]] | Exception | Callable[..., Any]


def configure_provider(**overrides: Any) -> WorkspaceSettings:
    save_api_key(TEST_API_KEY)
    record = WorkspaceSettings.load()
    record.default_model = TEST_MODEL
    for name, value in overrides.items():
        setattr(record, name, value)
    record.save()
    return record


class FakeLLM:
    """Stands in for ``openrouter.stream_chat``.

    Each step is a reply string (streamed in two chunks), a list of
    ``(tool_name, arguments)`` tool calls, an exception to raise, or a callable
    receiving the same keyword arguments as ``stream_chat``.
    """

    def __init__(self, *steps: Step) -> None:
        self.steps = list(steps)
        self.calls: list[dict[str, Any]] = []

    def __call__(self, messages: list[dict[str, Any]], **kwargs: Any) -> dict[str, Any]:
        tools = kwargs.get("tools") or []
        self.calls.append({
            "messages": json.loads(json.dumps(messages)),
            "model": kwargs.get("model"),
            "api_key": kwargs.get("api_key"),
            "tools": [tool["function"]["name"] for tool in tools],
        })
        if not self.steps:
            raise AssertionError("FakeLLM ran out of scripted steps")
        step = self.steps.pop(0)
        if callable(step) and not isinstance(step, type):
            return step(messages, **kwargs)
        if isinstance(step, Exception):
            raise step
        if isinstance(step, str):
            middle = len(step) // 2
            for chunk in (step[:middle], step[middle:]):
                if chunk:
                    kwargs["on_delta"](chunk)
            return {"message": {"role": "assistant", "content": step}, "finish_reason": "stop"}
        tool_calls = [
            {"id": f"call_{len(self.calls)}_{index}", "type": "function",
             "function": {"name": name, "arguments": json.dumps(arguments)}}
            for index, (name, arguments) in enumerate(step)
        ]
        return {"message": {"role": "assistant", "content": "", "tool_calls": tool_calls},
                "finish_reason": "tool_calls"}

    def tool_results(self, call_index: int) -> list[dict[str, Any]]:
        """Tool messages that were sent to the model on a given call."""
        return [m for m in self.calls[call_index]["messages"] if m["role"] == "tool"]


def read_events(response: Any) -> list[dict[str, Any]]:
    body = b"".join(response.streaming_content).decode()
    return [json.loads(line) for line in body.splitlines() if line.strip()]
