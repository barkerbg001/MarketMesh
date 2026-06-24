from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "MarketMesh API"
    debug: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]
    open_router_api_key: str | None = None
    open_router_model: str = "openai/gpt-4o-mini"
    playwright_headless: bool = False


settings = Settings()
