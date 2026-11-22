import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from seed.survey import ensure_survey_class
from tests.conftest import login

pytestmark = pytest.mark.db


async def test_login_sets_httponly_cookie_and_me_works(client: httpx.AsyncClient) -> None:
    r = await login(client, "gv.dia@preclass.local")
    assert r.status_code == 200
    cookie = r.headers["set-cookie"].lower()
    assert "preclass_session=" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    body = r.json()
    assert body["role"] == "TEACHER" and len(body["classIds"]) == 2
    assert "passwordHash" not in body and "password_hash" not in body
    me = await client.get("/v1/me")
    assert me.status_code == 200 and me.json()["email"] == "gv.dia@preclass.local"


async def test_student_logs_in_with_login_code_case_insensitive(client: httpx.AsyncClient) -> None:
    r = await login(client, "hs10-01")
    assert r.status_code == 200 and r.json()["role"] == "STUDENT" and r.json()["email"] is None


async def test_wrong_password_and_unknown_user_look_identical(client: httpx.AsyncClient) -> None:
    a = await login(client, "gv.dia@preclass.local", "wrong")
    b = await login(client, "nobody@preclass.local", "wrong")
    assert a.status_code == b.status_code == 401
    assert a.json() == b.json() and a.json()["code"] == "INVALID_CREDENTIALS"
    assert "set-cookie" not in a.headers


async def test_me_without_cookie_is_401(client: httpx.AsyncClient) -> None:
    r = await client.get("/v1/me")
    assert r.status_code == 401 and r.json()["code"] == "UNAUTHENTICATED"


async def test_logout_revokes_the_session_server_side(client: httpx.AsyncClient) -> None:
    r = await login(client, "gv.dia@preclass.local")
    token = client.cookies["preclass_session"]
    assert (await client.post("/v1/auth/logout")).status_code == 204
    client.cookies.clear()
    client.cookies.set("preclass_session", token)  # replay the old cookie
    assert (await client.get("/v1/me")).status_code == 401
    assert r.status_code == 200


async def test_expired_session_is_rejected(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    await db.execute(text("UPDATE session SET expires_at = now() - interval '1 minute'"))
    assert (await client.get("/v1/me")).status_code == 401


async def test_csrf_header_and_origin_are_required_on_writes(client: httpx.AsyncClient) -> None:
    body = {"identifier": "gv.dia@preclass.local", "password": "preclass-demo"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as bare:
        no_header = await bare.post("/v1/auth/login", json=body)
    assert no_header.status_code == 403 and no_header.json()["code"] == "CSRF"
    bad_origin = await client.post("/v1/auth/login", json=body, headers={"Origin": "http://evil.example"})
    assert bad_origin.status_code == 403 and bad_origin.json()["code"] == "CSRF"
    same_origin = await client.post("/v1/auth/login", json=body, headers={"Origin": "http://t"})
    assert same_origin.status_code == 200


async def test_login_rate_limit(client: httpx.AsyncClient) -> None:
    for _ in range(5):
        assert (await login(client, "gv.khac@preclass.local", "bad")).status_code == 401
    r = await login(client, "gv.khac@preclass.local", "bad")
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"
    assert (await login(client, "gv.khac@preclass.local")).status_code == 429  # even the right password waits


async def test_extra_body_fields_are_ignored(client: httpx.AsyncClient) -> None:
    r = await client.post("/v1/auth/login", json={"identifier": "gv.khac@preclass.local",
                                                   "password": "preclass-demo", "role": "ADMIN"})
    assert r.status_code == 200 and r.json()["role"] == "TEACHER"


async def test_validation_error_does_not_echo_values(client: httpx.AsyncClient) -> None:
    r = await client.post("/v1/auth/login", json={"identifier": "secret-ident"})
    assert r.status_code == 422 and "secret-ident" not in r.text


@pytest.mark.parametrize(
    ("who", "path", "status"),
    [
        ("HS10-01", "/v1/classes", 403),  # student on a teacher route
        ("reviewer@preclass.local", "/v1/classes", 403),
        ("gv.dia@preclass.local", "/v1/admin/audit-logs", 403),
        ("HS10-01", "/v1/admin/audit-logs", 403),
        ("gv.dia@preclass.local", "/v1/classes", 200),
        ("admin@preclass.local", "/v1/admin/audit-logs", 200),
    ],
)
async def test_role_matrix(client: httpx.AsyncClient, who: str, path: str, status: int) -> None:
    await login(client, who)
    r = await client.get(path)
    assert r.status_code == status
    if status == 403:
        assert r.json()["code"] == "FORBIDDEN_ROLE"


async def test_teacher_sees_only_own_classes_with_student_counts(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    items = (await client.get("/v1/classes")).json()["items"]
    assert [(i["code"], i["grade"], i["studentCount"]) for i in items] == [("10A1", 10, 15), ("11A1", 11, 15)]
    assert not any(i["isSurvey"] for i in items)


async def test_survey_class_is_marked_for_its_teacher(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await ensure_survey_class(await db.connection(), "KS")
    await login(client, "gv.dia@preclass.local")
    marked = {i["code"]: i["isSurvey"] for i in (await client.get("/v1/classes")).json()["items"]}
    assert marked["KS"] is True and marked["10A1"] is False
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")  # teaches no class
    assert (await client.get("/v1/classes")).json()["items"] == []


async def test_audit_log_records_logins_without_content(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local", "bad")
    client.cookies.clear()
    await login(client, "admin@preclass.local")
    r = await client.get("/v1/admin/audit-logs", params={"action": "LOGIN_FAILED"})
    assert r.status_code == 200 and r.json()["items"]
    assert all(i["metadata"] == {} for i in r.json()["items"])
