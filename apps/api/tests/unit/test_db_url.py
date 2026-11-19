from app.config import normalize_db_url


def test_neon_url_becomes_asyncpg_url() -> None:
    url = "postgresql://u:p@ep-x.ap-southeast-1.aws.neon.tech/preclass?sslmode=require&channel_binding=require"
    assert normalize_db_url(url) == "postgresql+asyncpg://u:p@ep-x.ap-southeast-1.aws.neon.tech/preclass?ssl=require"


def test_asyncpg_url_is_untouched() -> None:
    url = "postgresql+asyncpg://preclass:preclass@127.0.0.1:5432/preclass"
    assert normalize_db_url(url) == url


def test_deployed_env_requires_public_https_origin() -> None:
    import pytest

    from app.config import Settings

    for bad in ("http://localhost:3000", "http://pre-class-ai.vercel.app"):
        with pytest.raises(ValueError):
            Settings(app_env="demo", frontend_origin=bad, _env_file=None)
    Settings(app_env="demo", frontend_origin="https://pre-class-ai.vercel.app", _env_file=None)
    Settings(app_env="development", frontend_origin="http://localhost:3000", _env_file=None)
