from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"  # "production" disables the demo seed
    database_url: str = "postgresql+asyncpg://preclass:preclass@localhost:5432/preclass"
    session_secret: str = "replace-with-a-local-random-value"  # noqa: S105 dev placeholder; real value via env
    frontend_origin: str = "http://localhost:3000"
    cookie_secure: bool = True  # set COOKIE_SECURE=false for plain-http local dev
    session_ttl_hours: int = 8
    db_null_pool: bool = False  # tests: asyncpg connections must not outlive the per-test event loop
    upload_dir: str = "./data/uploads"
    llm_provider: str = "mock"  # mock | openai_compatible
    llm_base_url: str = ""  # openai_compatible: e.g. https://host/v1 (no trailing /chat/completions)
    llm_api_key: str = ""
    llm_model: str = ""
    ai_enabled: bool = True
    reviewer_enabled: bool = False  # second-person review (REVIEWER role); off by default
    mock_inject: str = ""  # fake_anchor,changed_quote,new_number,two_keys (tests)
    generation_daily_token_budget: int = 300_000


@lru_cache
def get_settings() -> Settings:
    return Settings()
