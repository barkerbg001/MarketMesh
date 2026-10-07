import json
import queue
import threading
from collections.abc import Iterator
from typing import Any

from django.conf import settings
from django.db import close_old_connections
from django.http import HttpResponse, StreamingHttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.renderers import JSONRenderer
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.personas import PERSONAS
from agents.run_registry import registry
from agents.runtime import TurnRunner, serialize_message
from core.exceptions import error_response
from research.models import Conversation, Message
from research.serializers import (
    ConversationCreateSerializer,
    ConversationUpdateSerializer,
    DeleteAllSerializer,
    SendMessageSerializer,
)

DEFAULT_TITLE = "New research"
HEARTBEAT_SECONDS = 15


def serialize_conversation(conversation: Conversation, *, with_messages: bool = False) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": str(conversation.pk),
        "title": conversation.title,
        "created_at": conversation.created_at.isoformat(),
        "updated_at": conversation.updated_at.isoformat(),
        "running": registry.is_active(str(conversation.pk)),
    }
    if with_messages:
        data["messages"] = [serialize_message(message) for message in conversation.messages.all()]
        context = conversation.research_context or {}
        data["product_count"] = len(context.get("products") or {})
        data["source_count"] = len(context.get("sources") or {})
    return data


def _close_interrupted(conversation: Conversation) -> None:
    """Messages left 'streaming' by a server restart can never finish."""
    if not registry.is_active(str(conversation.pk)):
        _mark_interrupted(conversation)


def _mark_interrupted(conversation: Conversation) -> None:
    for message in conversation.messages.filter(status=Message.Status.STREAMING):
        payload = dict(message.payload or {})
        payload["error"] = {"code": "interrupted", "message": "This response was interrupted before it finished."}
        message.status = Message.Status.CANCELLED
        message.payload = payload
        message.save(update_fields=["status", "payload"])


def _line(event: dict[str, Any]) -> bytes:
    return (json.dumps(event, ensure_ascii=False, default=str) + "\n").encode()


class ConversationListView(APIView):
    @extend_schema(tags=["conversations"], summary="List conversations, newest first",
                   operation_id="api_conversations_list")
    def get(self, request: Request) -> Response:
        return Response({"conversations": [serialize_conversation(c) for c in Conversation.objects.all()[:200]]})

    @extend_schema(request=ConversationCreateSerializer, tags=["conversations"], summary="Create a conversation")
    def post(self, request: Request) -> Response:
        serializer = ConversationCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation = Conversation.objects.create(title=serializer.validated_data.get("title") or DEFAULT_TITLE)
        return Response(serialize_conversation(conversation, with_messages=True), status=status.HTTP_201_CREATED)

    @extend_schema(request=DeleteAllSerializer, tags=["conversations"],
                   summary='Delete all conversations (requires {"confirm": "DELETE"})',
                   operation_id="api_conversations_destroy_all")
    def delete(self, request: Request) -> Response:
        serializer = DeleteAllSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        if registry.any_active():
            return error_response(status.HTTP_409_CONFLICT, "Stop the running research before deleting history.")
        deleted, _ = Conversation.objects.all().delete()
        return Response({"deleted": deleted})


class ConversationDetailView(APIView):
    @extend_schema(tags=["conversations"], summary="Get a conversation with its messages")
    def get(self, request: Request, conversation_id: str) -> Response:
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        _close_interrupted(conversation)
        return Response(serialize_conversation(conversation, with_messages=True))

    @extend_schema(request=ConversationUpdateSerializer, tags=["conversations"], summary="Rename a conversation")
    def patch(self, request: Request, conversation_id: str) -> Response:
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        serializer = ConversationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        conversation.title = serializer.validated_data["title"].strip() or DEFAULT_TITLE
        conversation.save(update_fields=["title", "updated_at"])
        return Response(serialize_conversation(conversation))

    @extend_schema(tags=["conversations"], summary="Delete a conversation")
    def delete(self, request: Request, conversation_id: str) -> Response:
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        if registry.is_active(str(conversation.pk)):
            return error_response(status.HTTP_409_CONFLICT, "Stop the running research before deleting it.")
        conversation.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NDJSONRenderer(JSONRenderer):
    """Lets clients ask for the event stream; validation and conflict errors still render as JSON."""

    media_type = "application/x-ndjson"
    format = "ndjson"


class ConversationMessagesView(APIView):
    renderer_classes = [JSONRenderer, NDJSONRenderer]

    @extend_schema(
        request=SendMessageSerializer,
        tags=["conversations"],
        summary="Send a message and stream agent events as NDJSON",
        description=(
            "Each line is a JSON event: run, agent_start, token, tool_start, tool_end, message, "
            "message_removed, cart_changed, error, ping, done."
        ),
        responses={(200, "application/x-ndjson"): str},
    )
    def post(self, request: Request, conversation_id: str) -> HttpResponse:
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        content: str = serializer.validated_data["content"]
        cart_item_ids: list[int] = serializer.validated_data["cart_item_ids"]

        handle = registry.start(str(conversation.pk))
        if handle is None:
            return error_response(
                status.HTTP_409_CONFLICT,
                "Agents are still working on this conversation. Wait or press Stop first.",
            )

        try:
            _mark_interrupted(conversation)
            user_message = Message.objects.create(
                conversation=conversation,
                role=Message.Role.USER,
                content=content,
                payload={"cart_item_ids": cart_item_ids} if cart_item_ids else {},
            )
            if conversation.title == DEFAULT_TITLE:
                conversation.title = _title_from(content)
            conversation.save(update_fields=["title", "updated_at"])
        except Exception:
            registry.finish(handle.run_id)
            raise

        start_event = {
            "type": "run",
            "run_id": handle.run_id,
            "conversation": serialize_conversation(conversation),
            "user_message": serialize_message(user_message),
        }
        runner = TurnRunner(conversation, user_message, emit=lambda e: None, cancel_event=handle.cancel_event,
                            cart_item_ids=cart_item_ids)

        if settings.CHAT_RUN_INLINE:
            events: list[dict[str, Any]] = [start_event]
            runner.emit = events.append
            try:
                final = runner.run()
            finally:
                registry.finish(handle.run_id)
            events.append({"type": "done", "status": final})
            return _stream_response(iter([_line(event) for event in events]))

        channel: queue.Queue[dict[str, Any] | None] = queue.Queue()
        runner.emit = channel.put

        def work() -> None:
            close_old_connections()
            final = "error"
            try:
                final = runner.run()
            finally:
                registry.finish(handle.run_id)
                channel.put({"type": "done", "status": final})
                channel.put(None)
                close_old_connections()

        threading.Thread(target=work, name=f"chat-run-{handle.run_id[:8]}", daemon=True).start()

        def stream() -> Iterator[bytes]:
            try:
                yield _line(start_event)
                while True:
                    try:
                        event = channel.get(timeout=HEARTBEAT_SECONDS)
                    except queue.Empty:
                        yield _line({"type": "ping"})
                        continue
                    if event is None:
                        break
                    yield _line(event)
            finally:
                # Runs when the turn ends or the client disconnects; stops a still-running turn.
                handle.cancel_event.set()

        return _stream_response(stream())


def _title_from(content: str) -> str:
    text = " ".join(content.split())
    return text if len(text) <= 60 else text[:57].rstrip() + "…"


def _stream_response(body: Iterator[bytes]) -> StreamingHttpResponse:
    response = StreamingHttpResponse(body, content_type="application/x-ndjson")
    response["Cache-Control"] = "no-cache"
    response["X-Accel-Buffering"] = "no"
    return response


class RunCancelView(APIView):
    @extend_schema(request=None, tags=["conversations"], summary="Stop a running chat turn")
    def post(self, request: Request, run_id: str) -> Response:
        if not registry.cancel(run_id):
            return Response({"cancelled": False, "detail": "That run already finished."})
        return Response({"cancelled": True})


def _speaker(message: Message) -> str:
    if message.role == Message.Role.USER:
        return "You"
    persona = PERSONAS.get(message.agent)
    return f"{persona.name} ({persona.role})" if persona else "Agent"


def conversation_markdown(conversation: Conversation) -> str:
    lines = [f"# {conversation.title}", "", f"Exported {timezone.now().isoformat()} from MarketMesh.", ""]
    for message in conversation.messages.all():
        lines += [f"## {_speaker(message)} · {message.created_at.isoformat()}", ""]
        if message.payload.get("task"):
            lines += [f"> Task from Mesh: {message.payload['task']}", ""]
        lines += [message.content or "_(no text)_", ""]
        if message.status != Message.Status.COMPLETE:
            lines += [f"_Status: {message.status}_", ""]
        products = message.payload.get("products") or []
        if products:
            lines.append("Products:")
            for product in products:
                price = product.get("price") or "price unknown"
                lines.append(
                    f"- [{product['title']}]({product['url']}) - {product.get('seller') or ''}, {price}"
                    f" (retrieved {product.get('retrieved_at') or 'unknown'})"
                )
            lines.append("")
        sources = message.payload.get("sources") or []
        if sources:
            lines.append("Sources:")
            lines += [f"- [{s.get('title') or s['url']}]({s['url']}) (retrieved {s.get('retrieved_at')})"
                      for s in sources]
            lines.append("")
    return "\n".join(lines)


class ConversationExportView(APIView):
    @extend_schema(
        tags=["conversations"],
        summary="Export a conversation as Markdown or JSON",
        parameters=[OpenApiParameter("format", str, enum=["markdown", "json"])],
    )
    def get(self, request: Request, conversation_id: str) -> HttpResponse:
        conversation = get_object_or_404(Conversation, pk=conversation_id)
        filename = f"marketmesh-conversation-{str(conversation.pk)[:8]}"
        export_format = request.query_params.get("format", "markdown")
        if export_format not in ("markdown", "json"):
            return error_response(status.HTTP_400_BAD_REQUEST, "format must be markdown or json.")
        if export_format == "json":
            response = HttpResponse(
                json.dumps(serialize_conversation(conversation, with_messages=True), indent=2, ensure_ascii=False),
                content_type="application/json",
            )
            response["Content-Disposition"] = f'attachment; filename="{filename}.json"'
            return response
        response = HttpResponse(conversation_markdown(conversation), content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{filename}.md"'
        return response


class ConversationExportAllView(APIView):
    @extend_schema(tags=["conversations"], summary="Export every conversation as JSON",
                   operation_id="api_conversations_export_all")
    def get(self, request: Request) -> HttpResponse:
        data = {
            "exported_at": timezone.now().isoformat(),
            "conversations": [serialize_conversation(c, with_messages=True) for c in Conversation.objects.all()],
        }
        response = HttpResponse(json.dumps(data, indent=2, ensure_ascii=False), content_type="application/json")
        response["Content-Disposition"] = 'attachment; filename="marketmesh-conversations.json"'
        return response
