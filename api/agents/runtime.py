"""Runs one chat turn: routing, agent tool loops, delegation, and persistence.

Interaction model: the user talks to Mesh (the orchestrator) by default. An
@mention of exactly one specialist routes the message straight to that
specialist. Only the orchestrator can delegate, at most ``max_delegations``
times per turn, never the same task twice, and specialists cannot delegate,
so agent-to-agent loops are impossible.
"""

import json
import logging
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from agents import prompts
from agents.personas import ORCHESTRATOR, PERSONAS, SPECIALISTS, resolve_handle
from agents.tools import ToolError, ToolOutput, UNTRUSTED_NOTE, toolset_for
from cart.models import CartItem
from cart.services import as_product
from catalog.products import compact, normalize_url
from core.crypto import EncryptionUnavailable
from core.services import openrouter
from core.services.openrouter import OpenRouterError, StreamCancelled
from research.models import Conversation, Message
from workspace.services import ProviderConfig, load_provider_config

logger = logging.getLogger(__name__)

Emit = Callable[[dict[str, Any]], None]

MAX_CONTEXT_PRODUCTS = 25
MAX_STORED_PRODUCTS = 200
MAX_STORED_SOURCES = 300
HISTORY_MESSAGES = 12

_MENTION = re.compile(r"(?<![\w@])@([A-Za-z]+)\b")
_CART_INTENT = re.compile(
    r"\b(add|put|save|place|keep|move|remove|delete|drop|take)\b[^.?!\n]{0,80}\b(cart|basket|shortlist)\b",
    re.IGNORECASE,
)
_LINK = re.compile(r"\[([^\]]+)\]\((\S+?)\)|(https?://[^\s<>()\[\]]+)")
_SPEAKER_PREFIX = re.compile(r"^\s*\[(?:Mesh|Scout|Tally|Atlas)[^\]]*\]:?\s*")


class RunCancelled(Exception):
    pass


@dataclass
class Route:
    agent: str
    mentioned: list[str]


def route_message(text: str) -> Route:
    """Pick who answers. One specialist mention goes direct; anything else goes to Mesh."""
    mentioned: list[str] = []
    for handle in _MENTION.findall(text):
        agent = resolve_handle(handle)
        if agent and agent not in mentioned:
            mentioned.append(agent)
    specialists = [agent for agent in mentioned if agent in SPECIALISTS]
    if len(specialists) == 1 and ORCHESTRATOR not in mentioned:
        return Route(agent=specialists[0], mentioned=mentioned)
    return Route(agent=ORCHESTRATOR, mentioned=specialists)


def wants_cart_change(text: str) -> bool:
    return bool(_CART_INTENT.search(text))


def _url_variants(url: str) -> set[str]:
    try:
        normalized = normalize_url(url)
    except ValueError:
        return {url}
    return {normalized, normalized.rstrip("/"), url.rstrip("/")}


def strip_unverified_links(text: str, allowed: set[str]) -> str:
    """Remove links to URLs that no tool retrieved in this conversation."""
    allowed_variants: set[str] = set()
    for url in allowed:
        allowed_variants |= _url_variants(url)

    def replace(match: re.Match[str]) -> str:
        label, url, bare = match.group(1), match.group(2), match.group(3)
        target = url or bare
        trimmed = target.rstrip(".,;:")
        if _url_variants(trimmed) & allowed_variants or _url_variants(target) & allowed_variants:
            return match.group(0)
        if label is not None:
            return label
        return "[unverified link removed]"

    return _LINK.sub(replace, text)


@dataclass
class AgentScratch:
    product_keys: list[str] = field(default_factory=list)
    source_urls: list[str] = field(default_factory=list)
    activity: list[dict[str, Any]] = field(default_factory=list)
    comparison: dict[str, Any] | None = None
    cart_actions: list[dict[str, Any]] = field(default_factory=list)

    def add_product(self, key: str) -> None:
        if key not in self.product_keys:
            self.product_keys.append(key)

    def add_source(self, url: str) -> None:
        if url not in self.source_urls:
            self.source_urls.append(url)


class _Segment:
    def __init__(self, message: Message) -> None:
        self.reset(message)

    def reset(self, message: Message) -> None:
        self.message = message
        self.parts: list[str] = []
        self.scratch = AgentScratch()


@dataclass
class RunContext:
    conversation: Conversation
    config: ProviderConfig
    emit: Emit
    cancel_event: threading.Event
    cart_writes_allowed: bool
    focus_keys: list[str]
    products: dict[str, dict[str, Any]] = field(default_factory=dict)
    sources: dict[str, dict[str, Any]] = field(default_factory=dict)
    pages: dict[str, Any] = field(default_factory=dict)
    delegations: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    delegation_count: int = 0
    cart_changed: bool = False
    run_specialist: Callable[[str, str], dict[str, Any]] = field(default=lambda agent, task: {})

    def cancelled(self) -> bool:
        return self.cancel_event.is_set()

    def check_cancelled(self) -> None:
        if self.cancelled():
            raise RunCancelled()

    def add_product(self, product: dict[str, Any]) -> None:
        self.products.pop(product["key"], None)
        self.products[product["key"]] = product

    def add_source(self, source: dict[str, Any]) -> None:
        self.sources.pop(source["url"], None)
        self.sources[source["url"]] = source

    def allowed_urls(self) -> set[str]:
        urls = set(self.sources)
        urls.update(product["url"] for product in self.products.values())
        return urls


def serialize_message(message: Message) -> dict[str, Any]:
    return {
        "id": message.pk,
        "conversation_id": str(message.conversation_id),
        "role": message.role,
        "agent": message.agent or None,
        "content": message.content,
        "status": message.status,
        "payload": message.payload or {},
        "created_at": message.created_at.isoformat(),
    }


def _history(conversation: Conversation, exclude_id: int | None, limit: int) -> list[dict[str, Any]]:
    rows = (
        conversation.messages.exclude(pk=exclude_id)
        .filter(status=Message.Status.COMPLETE)
        .exclude(content="")
        .order_by("-created_at", "-id")[:limit]
    )
    history = []
    for row in reversed(list(rows)):
        if row.role == Message.Role.USER:
            history.append({"role": "user", "content": row.content})
        else:
            persona = PERSONAS.get(row.agent)
            speaker = f"[{persona.name} - {persona.role}]" if persona else "[Agent]"
            history.append({"role": "assistant", "content": f"{speaker} {row.content}"})
    return history


def _context_block(ctx: RunContext) -> dict[str, Any]:
    recent = list(ctx.products.values())[-MAX_CONTEXT_PRODUCTS:][::-1]
    cart = [compact(as_product(item)) for item in CartItem.objects.all()[:30]]
    return {
        "role": "system",
        "content": prompts.context_message([compact(product) for product in recent], cart, ctx.focus_keys),
    }


def _tool_message(call_id: str, output: ToolOutput | None, error: str | None) -> dict[str, Any]:
    if error is not None:
        content: Any = {"error": error}
    elif output.untrusted:
        content = {"note": UNTRUSTED_NOTE, "result": output.data}
    else:
        content = output.data
    return {"role": "tool", "tool_call_id": call_id, "content": json.dumps(content, ensure_ascii=False, default=str)}


class TurnRunner:
    def __init__(self, conversation: Conversation, user_message: Message, emit: Emit, cancel_event: threading.Event,
                 cart_item_ids: list[int] | None = None) -> None:
        self.conversation = conversation
        self.user_message = user_message
        self.emit = emit
        self.cancel_event = cancel_event
        self.cart_item_ids = cart_item_ids or []

    def run(self) -> str:
        """Run the turn and return the final status: complete, cancelled, or error."""
        try:
            config = load_provider_config()
        except EncryptionUnavailable as exc:
            self.emit({"type": "error", "error": {"code": "encryption_unavailable", "message": str(exc)}})
            return "error"
        stored = self.conversation.research_context or {}
        ctx = RunContext(
            conversation=self.conversation,
            config=config,
            emit=self.emit,
            cancel_event=self.cancel_event,
            cart_writes_allowed=wants_cart_change(self.user_message.content),
            focus_keys=[],
            products=dict(stored.get("products") or {}),
            sources=dict(stored.get("sources") or {}),
        )
        for item in CartItem.objects.filter(pk__in=self.cart_item_ids):
            product = as_product(item)
            ctx.add_product(product)
            ctx.focus_keys.append(product["key"])
        ctx.run_specialist = lambda agent, task: self._delegate(ctx, agent, task)

        route = route_message(self.user_message.content)
        if ctx.cart_writes_allowed and route.agent != ORCHESTRATOR:
            # Only Mesh holds the cart tools.
            route = Route(agent=ORCHESTRATOR, mentioned=[route.agent])
        status = "complete"
        try:
            if not config.api_key:
                raise OpenRouterError(
                    "No OpenRouter API key is configured. Add one on the Settings page.", code="missing_key"
                )
            if not config.model_for(route.agent):
                raise OpenRouterError(
                    "No model is selected. Choose a default model on the Settings page.", code="missing_model"
                )
            self._run_agent(ctx, route.agent, task=None, requested=route.mentioned)
        except RunCancelled:
            status = "cancelled"
        except OpenRouterError as exc:
            status = "error"
            self.emit({"type": "error", "error": exc.to_dict()})
        except Exception:
            logger.exception("Chat turn failed")
            status = "error"
            self.emit({"type": "error", "error": {"code": "internal_error",
                                                  "message": "Something went wrong on the server. Try again."}})
        finally:
            self._persist_context(ctx)
            if ctx.cart_changed:
                self.emit({"type": "cart_changed"})
        return status

    def _persist_context(self, ctx: RunContext) -> None:
        products = dict(list(ctx.products.items())[-MAX_STORED_PRODUCTS:])
        sources = dict(list(ctx.sources.items())[-MAX_STORED_SOURCES:])
        self.conversation.research_context = {"products": products, "sources": sources}
        self.conversation.save(update_fields=["research_context", "updated_at"])

    def _delegate(self, ctx: RunContext, agent: str, task: str) -> dict[str, Any]:
        dedupe_key = (agent, re.sub(r"\s+", " ", task.lower()).strip())
        if dedupe_key in ctx.delegations:
            return {"note": "This exact task was already completed this turn; reuse the result.",
                    **ctx.delegations[dedupe_key]}
        if ctx.delegation_count >= ctx.config.max_delegations:
            raise ToolError(
                f"Delegation limit reached ({ctx.config.max_delegations} per message). Answer with what you have."
            )
        ctx.delegation_count += 1
        message = self._run_agent(ctx, agent, task=task, requested=[])
        result = {
            "agent": PERSONAS[agent].name,
            "findings": message.content[:4000],
            "product_keys": message.payload.get("product_keys", []),
            "showed_scorecard": bool(message.payload.get("comparison")),
        }
        ctx.delegations[dedupe_key] = result
        return result

    def _messages_for(self, ctx: RunContext, agent: str, task: str | None, requested: list[str],
                      exclude_id: int) -> list[dict[str, Any]]:
        can_delegate = agent == ORCHESTRATOR and task is None
        if agent == ORCHESTRATOR:
            system = prompts.orchestrator_prompt(
                ctx.config, cart_writes_allowed=ctx.cart_writes_allowed,
                can_delegate=can_delegate, requested=requested,
            )
        else:
            system = prompts.specialist_prompt(agent, ctx.config)
        messages: list[dict[str, Any]] = [{"role": "system", "content": system}, _context_block(ctx)]
        if task is None:
            messages += _history(self.conversation, exclude_id, HISTORY_MESSAGES)
        else:
            messages += [m for m in _history(self.conversation, exclude_id, 6) if m["role"] == "user"][-3:]
            messages.append({"role": "user", "content": f"Task from {PERSONAS[ORCHESTRATOR].name}: {task}"})
        return messages

    def _start_segment(self, agent: str, payload: dict[str, Any]) -> "_Segment":
        message = Message.objects.create(
            conversation=self.conversation, role=Message.Role.ASSISTANT, agent=agent,
            status=Message.Status.STREAMING, payload=dict(payload),
        )
        self.emit({"type": "agent_start", "message": serialize_message(message)})
        return _Segment(message)

    def _run_agent(self, ctx: RunContext, agent: str, *, task: str | None, requested: list[str]) -> Message:
        """Run one agent's tool loop and return its (last) message.

        The orchestrator's output is split into a new message after each delegation
        round, so the thread reads in order: plan, specialist reports, synthesis.
        """
        ctx.check_cancelled()
        base_payload: dict[str, Any] = {}
        if task is not None:
            base_payload.update(task=task, delegated_by=ORCHESTRATOR)
        if agent == ORCHESTRATOR and requested:
            base_payload["requested"] = requested
        segment = self._start_segment(agent, base_payload)

        toolset = toolset_for(
            agent, retailers_enabled=ctx.config.retailers_enabled,
            cart_writes_allowed=ctx.cart_writes_allowed and agent == ORCHESTRATOR,
            can_delegate=agent == ORCHESTRATOR and task is None,
        )
        messages = self._messages_for(ctx, agent, task, requested, exclude_id=segment.message.pk)

        def on_delta(text: str) -> None:
            segment.parts.append(text)
            self.emit({"type": "token", "message_id": segment.message.pk, "text": text})

        try:
            rounds = ctx.config.max_tool_rounds
            for round_index in range(rounds + 1):
                ctx.check_cancelled()
                final_round = round_index == rounds
                if final_round:
                    messages.append({"role": "system", "content":
                                     "Tool budget used up. Answer now with what you have and say what is missing."})
                if segment.parts and not segment.parts[-1].endswith("\n"):
                    on_delta("\n\n")
                result = openrouter.stream_chat(
                    messages,
                    api_key=ctx.config.api_key,
                    model=ctx.config.model_for(agent),
                    tools=None if final_round else (toolset.schemas() or None),
                    temperature=ctx.config.temperature,
                    max_tokens=ctx.config.max_tokens,
                    timeout=ctx.config.request_timeout,
                    on_delta=on_delta,
                    should_cancel=ctx.cancelled,
                )
                assistant = result["message"]
                calls = assistant.get("tool_calls") or []
                if not calls:
                    break
                messages.append(assistant)
                for call in calls:
                    ctx.check_cancelled()
                    messages.append(self._execute(ctx, segment.scratch, toolset, segment.message, call))
                delegated = any(call.get("function", {}).get("name") == "delegate" for call in calls)
                if agent == ORCHESTRATOR and delegated:
                    self._close_segment(segment, ctx)
                    segment.reset(self._start_segment(agent, base_payload).message)
        except StreamCancelled:
            self._finish(segment.message, ctx, segment.scratch, segment.parts, Message.Status.CANCELLED)
            raise RunCancelled() from None
        except RunCancelled:
            self._finish(segment.message, ctx, segment.scratch, segment.parts, Message.Status.CANCELLED)
            raise
        except OpenRouterError as exc:
            self._finish(segment.message, ctx, segment.scratch, segment.parts, Message.Status.ERROR,
                         error=exc.to_dict())
            raise
        except Exception:
            self._finish(segment.message, ctx, segment.scratch, segment.parts, Message.Status.ERROR,
                         error={"code": "internal_error", "message": "This agent hit an unexpected error."})
            raise

        if not "".join(segment.parts).strip():
            segment.parts.append("I could not produce an answer from the available information.")
        self._finish(segment.message, ctx, segment.scratch, segment.parts, Message.Status.COMPLETE)
        return segment.message

    def _close_segment(self, segment: "_Segment", ctx: RunContext) -> None:
        """Finish a pre-delegation orchestrator message, or drop it if it only delegated."""
        only_delegation = all(entry["tool"] == "delegate" for entry in segment.scratch.activity)
        if "".join(segment.parts).strip() or not only_delegation:
            self._finish(segment.message, ctx, segment.scratch, segment.parts, Message.Status.COMPLETE)
        else:
            message_id = segment.message.pk
            segment.message.delete()
            self.emit({"type": "message_removed", "message_id": message_id})

    def _execute(self, ctx: RunContext, scratch: AgentScratch, toolset, message: Message,
                 call: dict[str, Any]) -> dict[str, Any]:
        name = call.get("function", {}).get("name", "")
        tool = toolset.get(name)
        label = tool.label if tool else name
        self.emit({"type": "tool_start", "message_id": message.pk, "tool": name, "label": label})
        output: ToolOutput | None = None
        error: str | None = None
        if tool is None:
            error = f"Tool '{name}' is not available to you."
        else:
            try:
                raw = call["function"].get("arguments") or "{}"
                args = json.loads(raw)
                if not isinstance(args, dict):
                    raise ValueError
            except ValueError:
                error = "Tool arguments must be a JSON object."
            else:
                try:
                    output = tool.handler(ctx, scratch, args)
                except ToolError as exc:
                    error = str(exc)
                except (RunCancelled, OpenRouterError):
                    raise
                except Exception:
                    logger.exception("Tool %s failed", name)
                    error = f"{label} failed unexpectedly."
        entry = {"tool": name, "label": label, "ok": error is None,
                 "summary": output.summary if output else error}
        scratch.activity.append(entry)
        self.emit({"type": "tool_end", "message_id": message.pk, **entry})
        return _tool_message(call.get("id", ""), output, error)

    def _finish(self, message: Message, ctx: RunContext, scratch: AgentScratch, parts: list[str], status: str,
                error: dict[str, Any] | None = None) -> None:
        content = _SPEAKER_PREFIX.sub("", "".join(parts)).strip()
        content = strip_unverified_links(content, ctx.allowed_urls())
        payload = dict(message.payload or {})
        payload.update(
            product_keys=scratch.product_keys,
            products=[ctx.products[key] for key in scratch.product_keys if key in ctx.products],
            sources=[ctx.sources[url] for url in scratch.source_urls if url in ctx.sources],
            activity=scratch.activity,
        )
        if scratch.comparison:
            comparison = dict(scratch.comparison)
            comparison["products"] = [ctx.products[key] for key in comparison["product_keys"] if key in ctx.products]
            payload["comparison"] = comparison
        if scratch.cart_actions:
            payload["cart_actions"] = scratch.cart_actions
        if error:
            payload["error"] = error
        message.content = content
        message.status = status
        message.payload = payload
        message.save(update_fields=["content", "status", "payload"])
        self.emit({"type": "message", "message": serialize_message(message)})
