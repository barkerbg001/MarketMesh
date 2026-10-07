import re

from rest_framework import serializers

from agents.personas import PERSONAS
from workspace.models import CURRENCY_CHOICES, GENERATION_LIMITS, RESEARCH_REGIONS

_MODEL_ID = re.compile(r"^[A-Za-z0-9._\-/:]+$")


def _validate_model_id(value: str) -> str:
    if value and (len(value) > 200 or not _MODEL_ID.match(value)):
        raise serializers.ValidationError("Not a valid OpenRouter model ID.")
    return value


class ApiKeySerializer(serializers.Serializer):
    api_key = serializers.CharField(min_length=20, max_length=300, trim_whitespace=True)

    def validate_api_key(self, value: str) -> str:
        if any(character.isspace() for character in value):
            raise serializers.ValidationError("The key must not contain spaces.")
        return value


class TestKeySerializer(serializers.Serializer):
    api_key = serializers.CharField(min_length=20, max_length=300, required=False, trim_whitespace=True)


def _range_field(name: str, field_class: type[serializers.Field]) -> serializers.Field:
    low, high = GENERATION_LIMITS[name]
    return field_class(min_value=low, max_value=high, required=False)


class SettingsUpdateSerializer(serializers.Serializer):
    default_model = serializers.CharField(max_length=200, allow_blank=True, required=False,
                                          validators=[_validate_model_id])
    agent_models = serializers.DictField(child=serializers.CharField(max_length=200, allow_blank=True),
                                         required=False)
    temperature = _range_field("temperature", serializers.FloatField)
    max_tokens = _range_field("max_tokens", serializers.IntegerField)
    max_tool_rounds = _range_field("max_tool_rounds", serializers.IntegerField)
    max_delegations = _range_field("max_delegations", serializers.IntegerField)
    request_timeout = _range_field("request_timeout", serializers.IntegerField)
    research_region = serializers.ChoiceField(choices=RESEARCH_REGIONS, required=False)
    currency = serializers.ChoiceField(choices=CURRENCY_CHOICES, required=False)

    def validate_agent_models(self, value: dict[str, str]) -> dict[str, str]:
        unknown = set(value) - set(PERSONAS)
        if unknown:
            raise serializers.ValidationError(f"Unknown agents: {', '.join(sorted(unknown))}.")
        for model in value.values():
            _validate_model_id(model)
        return {agent: model for agent, model in value.items() if model}
