"""Pre-launch hardening: stricter admin login, admin audit, response headers, docs access, guest threshold warnings."""

import logging

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.guest import create_limiter, resume_limiter
from seed.survey import ensure_survey_class
from tests.conftest import login

pytestmark = pytest.mark.db


async def test_admin_login_locks_after_3_wrong_passwords_but_teachers_get_5(client: httpx.AsyncClient) -> None:
    for _ in range(3):
        assert (await login(client, "admin@preclass.local", "bad")).status_code == 401
    r = await login(client, "admin@preclass.local", "bad")
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"
    assert (await login(client, "admin@preclass.local")).status_code == 429  # even the right password waits
    for _ in range(3):  # a teacher is still on the ordinary limit
        assert (await login(client, "gv.khac@preclass.local", "bad")).status_code == 401
    assert (await login(client, "gv.khac@preclass.local")).status_code == 200


async def test_admin_actions_are_audited(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "admin@preclass.local")
    assert (await client.get("/v1/admin/audit-logs")).status_code == 200
    assert (await client.get("/v1/admin/survey/stats")).status_code == 200
    assert (await client.get("/v1/admin/survey/export.csv")).status_code == 200
    actions = {i["action"] for i in (await client.get("/v1/admin/audit-logs?limit=50")).json()["items"]}
    assert {"LOGIN", "ADMIN_VIEW_AUDIT_LOGS", "ADMIN_VIEW_SURVEY_STATS", "EXPORT_SURVEY"} <= actions


async def test_survey_stats_is_admin_only(client: httpx.AsyncClient) -> None:
    for who in ("gv.dia@preclass.local", "HS10-01"):
        client.cookies.clear()
        await login(client, who)
        assert (await client.get("/v1/admin/survey/stats")).status_code == 403
    client.cookies.clear()
    await login(client, "admin@preclass.local")
    body = (await client.get("/v1/admin/survey/stats")).json()
    assert set(body) == {"activeGuests", "createdLastHour", "maxActive", "createPerHourPerIp", "chatTotal", "chatFallbackRate",
                         "chatBlocked", "chatTokensIn", "chatTokensOut"}


async def test_user_data_is_never_cached_and_nosniff_everywhere(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    for path in ("/v1/me", "/v1/lessons", "/v1/sources"):
        h = (await client.get(path)).headers
        assert h["cache-control"] == "no-store" and h["x-content-type-options"] == "nosniff", path
    health = await client.get("/v1/health")
    assert health.headers["x-content-type-options"] == "nosniff" and "no-store" not in health.headers.get("cache-control", "")


@pytest.mark.parametrize(
    ("mode", "who", "docs", "spec"),
    [
        ("open", None, 200, 200),
        ("staff", None, 401, 401),
        ("staff", "HS10-01", 404, 404),
        ("staff", "gv.dia@preclass.local", 200, 200),
        ("staff", "admin@preclass.local", 200, 200),
        ("off", "admin@preclass.local", 404, 404),
    ],
)
async def test_docs_access_modes(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch, mode: str, who: str | None,
                                 docs: int, spec: int) -> None:
    monkeypatch.setenv("DOCS_ACCESS", mode)
    get_settings.cache_clear()
    try:
        if who:
            await login(client, who)
        assert (await client.get("/docs")).status_code == docs
        assert (await client.get("/v1/openapi.json")).status_code == spec
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


def test_docs_default_is_open_except_in_production(monkeypatch: pytest.MonkeyPatch) -> None:
    for env, expected in (("development", "open"), ("demo", "open"), ("production", "off")):
        monkeypatch.setenv("APP_ENV", env)
        monkeypatch.setenv("FRONTEND_ORIGIN", "https://pre-class-ai.vercel.app")
        monkeypatch.delenv("DOCS_ACCESS", raising=False)
        get_settings.cache_clear()
        assert get_settings().docs_mode == expected, env
    monkeypatch.undo()
    get_settings.cache_clear()


async def test_guest_creation_warns_at_80_percent_without_leaking_ip_or_code(
        client: httpx.AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture) -> None:
    monkeypatch.setenv("GUEST_ACCESS_ENABLED", "true")
    monkeypatch.setenv("GUEST_CREATE_PER_HOUR", "5")
    monkeypatch.setenv("GUEST_MAX_ACTIVE", "5")
    get_settings.cache_clear()
    create_limiter.reset()
    resume_limiter.reset()
    await ensure_survey_class(await db.connection(), "KS")
    try:
        with caplog.at_level(logging.WARNING, logger="preclass.guest"):
            codes = []
            for _ in range(3):
                client.cookies.clear()
                codes.append((await client.post("/v1/auth/guest", json={})).json()["surveyCode"])
            assert not caplog.records  # 3 of 5 = 60%
            client.cookies.clear()
            codes.append((await client.post("/v1/auth/guest", json={})).json()["surveyCode"])  # 4 of 5 = 80%
        msgs = " ".join(r.getMessage() for r in caplog.records)
        assert "guest creation" in msgs and "active guests" in msgs
        assert not any(c in msgs for c in codes) and "127.0.0.1" not in msgs
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        create_limiter.reset()
