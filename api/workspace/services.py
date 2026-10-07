from dataclasses import dataclass, field

from django.conf import settings
from django.utils import timezone

from core import crypto
from workspace.models import RESEARCH_REGIONS, WorkspaceSettings


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str | None
    key_source: str  # "settings", "environment", or "none"
    default_model: str
    agent_models: dict[str, str] = field(default_factory=dict)
    temperature: float = 0.3
    max_tokens: int = 1500
    max_tool_rounds: int = 5
    max_delegations: int = 3
    request_timeout: int = 60
    research_region: str = "za-en"
    currency: str = "ZAR"

    def model_for(self, agent_id: str) -> str:
        return self.agent_models.get(agent_id) or self.default_model

    @property
    def region_label(self) -> str:
        return dict(RESEARCH_REGIONS).get(self.research_region, self.research_region)

    @property
    def retailers_enabled(self) -> bool:
        """The built-in retailer scrapers only cover South Africa."""
        return self.research_region == "za-en"


def stored_api_key(record: WorkspaceSettings) -> str | None:
    if not record.encrypted_api_key:
        return None
    return crypto.decrypt(record.encrypted_api_key)


def load_provider_config() -> ProviderConfig:
    record = WorkspaceSettings.load()
    api_key = stored_api_key(record)
    source = "settings"
    if not api_key:
        api_key = settings.OPEN_ROUTER_API_KEY
        source = "environment" if api_key else "none"
    return ProviderConfig(
        api_key=api_key,
        key_source=source,
        default_model=record.default_model or settings.OPEN_ROUTER_MODEL,
        agent_models={k: v for k, v in (record.agent_models or {}).items() if v},
        temperature=record.temperature,
        max_tokens=record.max_tokens,
        max_tool_rounds=record.max_tool_rounds,
        max_delegations=record.max_delegations,
        request_timeout=record.request_timeout,
        research_region=record.research_region,
        currency=record.currency,
    )


def save_api_key(api_key: str) -> WorkspaceSettings:
    record = WorkspaceSettings.load()
    record.encrypted_api_key = crypto.encrypt(api_key)
    record.api_key_hint = api_key[-4:]
    record.api_key_updated_at = timezone.now()
    record.save(update_fields=["encrypted_api_key", "api_key_hint", "api_key_updated_at", "updated_at"])
    return record


def clear_api_key() -> WorkspaceSettings:
    record = WorkspaceSettings.load()
    record.encrypted_api_key = ""
    record.api_key_hint = ""
    record.api_key_updated_at = None
    record.save(update_fields=["encrypted_api_key", "api_key_hint", "api_key_updated_at", "updated_at"])
    return record


def key_status(record: WorkspaceSettings) -> dict:
    """Masked key state. Never includes the key itself."""
    if record.encrypted_api_key:
        return {
            "configured": True,
            "source": "settings",
            "hint": f"…{record.api_key_hint}" if record.api_key_hint else None,
            "updated_at": record.api_key_updated_at.isoformat() if record.api_key_updated_at else None,
            "environment_fallback": bool(settings.OPEN_ROUTER_API_KEY),
        }
    if settings.OPEN_ROUTER_API_KEY:
        return {
            "configured": True,
            "source": "environment",
            "hint": None,
            "updated_at": None,
            "environment_fallback": True,
        }
    return {
        "configured": False,
        "source": "none",
        "hint": None,
        "updated_at": None,
        "environment_fallback": False,
    }
