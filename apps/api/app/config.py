from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://preclass:preclass@localhost:5432/preclass"
    session_secret: str = "replace-with-a-local-random-value"  # noqa: S105 dev placeholder; real value via env
    frontend_origin: str = "http://localhost:3000"
    upload_dir: str = "./data/uploads"
    llm_provider: str = "mock"  # mock | openai_compatible
    ai_enabled: bool = True
    generation_daily_token_budget: int = 300_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
