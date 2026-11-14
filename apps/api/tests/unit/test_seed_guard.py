import pytest

from app.config import get_settings
from seed.seed import main


async def test_seed_refuses_production(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    try:
        with pytest.raises(SystemExit, match="APP_ENV=production"):
            await main()
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
