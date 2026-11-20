import httpx
import pytest

from app.main import app


async def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_health_ok() -> None:
    async with await _client() as c:
        r = await c.get("/v1/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"


async def test_health_reports_the_deployed_commit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    async with await _client() as c:
        assert (await c.get("/v1/health")).json()["commit"] == "dev"
        monkeypatch.setenv("RENDER_GIT_COMMIT", "4199c7d0123456789abcdef")
        assert (await c.get("/v1/health")).json() == {"status": "ok", "commit": "4199c7d"}


async def test_health_accepts_head_with_no_body() -> None:
    async with await _client() as c:
        r = await c.head("/v1/health")
    assert r.status_code == 200 and r.content == b""


async def test_unknown_route_is_problem_json() -> None:
    async with await _client() as c:
        r = await c.get("/v1/nope")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "NOT_FOUND"
