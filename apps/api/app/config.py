from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_db_url(url: str) -> str:
    """Accept a provider URL (Neon/Render: postgres://…?sslmode=require&channel_binding=…) and make it asyncpg-ready."""
    parts = urlsplit(url)
    scheme = "postgresql+asyncpg" if parts.scheme in ("postgres", "postgresql") else parts.scheme
    q = [(k, v) for k, v in parse_qsl(parts.query) if k != "channel_binding"]
    q = [("ssl", v) if k == "sslmode" else (k, v) for k, v in q]  # asyncpg spells it `ssl`
    return urlunsplit((scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"  # "production" disables the demo seed
    database_url: str = "postgresql+asyncpg://preclass:preclass@localhost:5432/preclass"
    session_secret: str = "replace-with-a-local-random-value"  # noqa: S105 dev placeholder; real value via env
    frontend_origin: str = "http://localhost:3000"
    cookie_secure: bool = True  # set COOKIE_SECURE=false for plain-http local dev
    session_ttl_hours: int = 8
    db_pool_size: int = 10  # Neon free demo: 5 (render.yaml)
    db_max_overflow: int = 5  # Neon free demo: 0
    db_pool_recycle: int = 1800  # Neon free demo: 300 (idle connections are closed server-side)
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
    guest_access_enabled: bool = False  # anonymous survey access (POST /v1/auth/guest); 404 when off
    guest_class_code: str = "KS"  # survey class guests join; its assignments are created by `python -m seed.survey`
    guest_max_active: int = 500  # guests seen in the last 14 days; beyond it new guests get 503
    guest_create_per_hour: int = 60  # per real client IP; a classroom shares one Wi-Fi (NAT), so keep it generous
    guest_session_days: int = 14
    demo_replay: bool = False  # DEMO_REPLAY: teacher analysis answers with a recorded sample (no network), labelled "replay"
    chat_enabled: bool = False  # Habit (hints + chat) for students; every Habit route is 404 when off
    chat_mode: str = "rule"  # rule (free, deterministic) | llm (rule guards + LLM wording; falls back to rule)
    chat_max_per_day_per_student: int = 30
    chat_max_per_item: int = 6
    chat_llm_base_url: str = ""
    chat_llm_api_key: str = ""
    chat_llm_model: str = ""
    chat_max_output_tokens: int = 220
    chat_daily_token_budget: int = 300_000
    habit_daily_goal: int = 3
    chat_ai_extra: bool = False  # CHAT_MODE=llm only: a second, clearly labelled part with general knowledge (unverified)
    personalization_enabled: bool = False  # student-chosen options, focus mode, behaviour-based hints; 404 when off
    source_max_pdf_pages: int = 50  # uploaded PDF / XLSX / PPTX limits (docs/security/THREAT-MODEL-upload.md)
    source_max_xlsx_sheets: int = 5
    source_max_xlsx_cells: int = 2000  # non-empty cells per sheet
    source_max_pptx_slides: int = 60
    source_parse_timeout_s: int = 30  # parser child process is killed after this
    source_parse_mem_mb: int = 600  # RLIMIT_AS of the parser child (Linux only; 0 = no limit)
    docs_access: str = ""  # who may open /docs and /v1/openapi.json: open | staff (logged-in teacher/reviewer/admin) | off.
    # Unset: "open" everywhere except APP_ENV=production, where it is "off".

    @model_validator(mode="after")
    def _public_origin_when_deployed(self) -> "Settings":
        if self.app_env.lower() in ("demo", "production", "prod"):
            u = urlsplit(self.frontend_origin)
            if u.scheme != "https" or u.hostname in (None, "localhost", "127.0.0.1", "::1"):
                raise ValueError(f"FRONTEND_ORIGIN must be public https when APP_ENV={self.app_env}: {self.frontend_origin!r}")
        return self

    @field_validator("chat_mode")
    @classmethod
    def _chat_mode(cls, v: str) -> str:
        if v not in ("rule", "llm"):
            raise ValueError("CHAT_MODE must be rule or llm")
        return v

    @field_validator("docs_access")
    @classmethod
    def _docs_access(cls, v: str) -> str:
        if v not in ("", "open", "staff", "off"):
            raise ValueError("DOCS_ACCESS must be open, staff or off")
        return v

    @property
    def docs_mode(self) -> str:
        return self.docs_access or ("off" if self.app_env.lower() in ("production", "prod") else "open")

    @field_validator("database_url")
    @classmethod
    def _db_url(cls, v: str) -> str:
        return normalize_db_url(v)


@lru_cache
def get_settings() -> Settings:
    return Settings()
