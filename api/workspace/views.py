import logging
from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from agents.personas import AVATAR_STYLE, PERSONAS
from core.crypto import EncryptionUnavailable
from core.exceptions import error_response
from core.services import openrouter
from core.services.openrouter import OpenRouterError
from workspace.models import CURRENCY_CHOICES, GENERATION_LIMITS, RESEARCH_REGIONS, WorkspaceSettings
from workspace.serializers import ApiKeySerializer, SettingsUpdateSerializer, TestKeySerializer
from workspace.services import clear_api_key, key_status, load_provider_config, save_api_key

logger = logging.getLogger(__name__)

EDITABLE_FIELDS = (
    "default_model", "agent_models", "temperature", "max_tokens", "max_tool_rounds",
    "max_delegations", "request_timeout", "research_region", "currency",
)


def settings_payload(record: WorkspaceSettings) -> dict[str, Any]:
    return {
        "openrouter": key_status(record),
        "default_model": record.default_model,
        "agent_models": record.agent_models or {},
        "generation": {
            "temperature": record.temperature,
            "max_tokens": record.max_tokens,
            "max_tool_rounds": record.max_tool_rounds,
            "max_delegations": record.max_delegations,
            "request_timeout": record.request_timeout,
        },
        "limits": {name: {"min": low, "max": high} for name, (low, high) in GENERATION_LIMITS.items()},
        "research_region": record.research_region,
        "currency": record.currency,
        "options": {
            "regions": [{"value": value, "label": label} for value, label in RESEARCH_REGIONS],
            "currencies": [{"value": value, "label": label} for value, label in CURRENCY_CHOICES],
        },
    }


def _encryption_error(exc: EncryptionUnavailable) -> Response:
    logger.error("Encryption unavailable: %s", exc)
    return error_response(status.HTTP_500_INTERNAL_SERVER_ERROR, {"code": "encryption_unavailable",
                                                                  "message": str(exc)})


class SettingsView(APIView):
    @extend_schema(tags=["settings"], summary="Get workspace settings (the API key is never returned)")
    def get(self, request: Request) -> Response:
        return Response(settings_payload(WorkspaceSettings.load()))

    @extend_schema(request=SettingsUpdateSerializer, tags=["settings"], summary="Update models and preferences")
    def patch(self, request: Request) -> Response:
        serializer = SettingsUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        record = WorkspaceSettings.load()
        changed = [name for name in EDITABLE_FIELDS if name in serializer.validated_data]
        for name in changed:
            setattr(record, name, serializer.validated_data[name])
        if changed:
            record.save(update_fields=[*changed, "updated_at"])
        return Response(settings_payload(record))


class ApiKeyView(APIView):
    @extend_schema(request=ApiKeySerializer, tags=["settings"], summary="Save or replace the OpenRouter API key")
    def put(self, request: Request) -> Response:
        serializer = ApiKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            record = save_api_key(serializer.validated_data["api_key"])
        except EncryptionUnavailable as exc:
            return _encryption_error(exc)
        return Response(settings_payload(record))

    @extend_schema(tags=["settings"], summary="Remove the saved OpenRouter API key")
    def delete(self, request: Request) -> Response:
        return Response(settings_payload(clear_api_key()))


class TestConnectionView(APIView):
    @extend_schema(request=TestKeySerializer, tags=["settings"],
                   summary="Test an OpenRouter key (the given one, or the saved one)")
    def post(self, request: Request) -> Response:
        serializer = TestKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        candidate = serializer.validated_data.get("api_key")
        try:
            api_key = candidate or load_provider_config().api_key
            details = openrouter.check_key(api_key)
        except EncryptionUnavailable as exc:
            return _encryption_error(exc)
        except OpenRouterError as exc:
            return Response({"ok": False, "error": exc.to_dict()})
        return Response({"ok": True, "details": details})


class ModelListView(APIView):
    @extend_schema(tags=["settings"], summary="OpenRouter models that support tool calling")
    def get(self, request: Request) -> Response:
        try:
            models = openrouter.list_models(refresh=request.query_params.get("refresh") == "1")
        except OpenRouterError as exc:
            return error_response(status.HTTP_502_BAD_GATEWAY, exc.to_dict())
        return Response({"models": models})


class AgentListView(APIView):
    @extend_schema(tags=["agents"], summary="The agent roster with personalities and avatar seeds")
    def get(self, request: Request) -> Response:
        return Response({"avatar_style": AVATAR_STYLE, "agents": [p.to_dict() for p in PERSONAS.values()]})
