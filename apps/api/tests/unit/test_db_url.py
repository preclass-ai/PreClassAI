from app.config import normalize_db_url


def test_neon_url_becomes_asyncpg_url() -> None:
    url = "postgresql://u:p@ep-x.ap-southeast-1.aws.neon.tech/preclass?sslmode=require&channel_binding=require"
    assert normalize_db_url(url) == "postgresql+asyncpg://u:p@ep-x.ap-southeast-1.aws.neon.tech/preclass?ssl=require"


def test_asyncpg_url_is_untouched() -> None:
    url = "postgresql+asyncpg://preclass:preclass@127.0.0.1:5432/preclass"
    assert normalize_db_url(url) == url
