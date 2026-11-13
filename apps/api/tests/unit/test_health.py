import httpx

from app.main import app


async def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t")


async def test_health_ok() -> None:
    async with await _client() as c:
        r = await c.get("/v1/health")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


async def test_unknown_route_is_problem_json() -> None:
    async with await _client() as c:
        r = await c.get("/v1/nope")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/problem+json")
    assert r.json()["code"] == "NOT_FOUND"
