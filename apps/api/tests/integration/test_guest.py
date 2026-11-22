"""Anonymous survey guests: creation, isolation, role limits, rate limits, resume, export without PII, feature flag."""

import re
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.guest import create_limiter, resume_limiter
from app.ids import uid
from seed.survey import ensure_survey_class
from tests.conftest import login

pytestmark = pytest.mark.db

KS_ASSIGN = uid(f"{uid('dan-so-vung:published')}:assignment:KS")
CODE = re.compile(r"^KS-[A-HJ-NP-Z2-9]{4}$")


@pytest.fixture
async def guests_on(monkeypatch: pytest.MonkeyPatch, db: AsyncSession) -> AsyncIterator[None]:
    monkeypatch.setenv("GUEST_ACCESS_ENABLED", "true")
    get_settings.cache_clear()
    create_limiter.reset()
    resume_limiter.reset()
    assert await ensure_survey_class(await db.connection(), "KS") == 1
    try:
        yield
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        create_limiter.reset()
        resume_limiter.reset()


async def new_guest(c: httpx.AsyncClient, **body: Any) -> dict[str, Any]:
    c.cookies.clear()
    r = await c.post("/v1/auth/guest", json=body)
    assert r.status_code == 201, r.text
    return dict(r.json())


async def answer_first_mcq(c: httpx.AsyncClient, assignment: str) -> dict[str, Any]:
    d = (await c.get(f"/v1/student/assignments/{assignment}")).json()
    item = next(i for i in d["items"] if i["itemType"] == "MCQ")
    r = await c.post(f"/v1/student/assignments/{assignment}/attempts",
                     json={"itemId": item["id"], "answer": {"choice": "A"}, "requestId": str(uuid.uuid4())})
    assert r.status_code == 201, r.text
    return dict(r.json())


async def test_flag_off_means_404_everywhere(client: httpx.AsyncClient) -> None:
    assert (await client.get("/v1/auth/config")).json() == {"guestEnabled": False, "chatEnabled": False, "personalizationEnabled": False, "chatMode": "rule", "aiProvider": None}
    assert (await client.post("/v1/auth/guest", json={})).status_code == 404
    assert (await client.post("/v1/auth/guest/resume", json={"surveyCode": "KS-ABCD"})).status_code == 404


async def test_guest_gets_code_cookie_and_the_survey_assignment(client: httpx.AsyncClient, guests_on: None) -> None:
    assert (await client.get("/v1/auth/config")).json() == {"guestEnabled": True, "chatEnabled": False, "personalizationEnabled": False, "chatMode": "rule", "aiProvider": None}
    g = await new_guest(client, lessonKey="dan-so-vung")
    assert CODE.match(g["surveyCode"]) and g["assignmentId"] == str(KS_ASSIGN)
    assert g["user"]["isGuest"] and g["user"]["role"] == "STUDENT" and g["user"]["email"] is None
    assert g["user"]["displayName"] == f"Khách {g['surveyCode'][3:]}"
    set_cookie = (await client.post("/v1/auth/guest", json={})).headers["set-cookie"]
    assert "HttpOnly" in set_cookie and f"Max-Age={14 * 86400}" in set_cookie
    me = (await client.get("/v1/me")).json()
    assert me["isGuest"] and me["surveyCode"] and me["loginCode"] == me["surveyCode"]
    items = (await client.get("/v1/student/assignments")).json()["items"]
    assert [str(i["id"]) for i in items] == [str(KS_ASSIGN)]
    res = await answer_first_mcq(client, str(KS_ASSIGN))
    assert res["explanation"]  # explanation only after answering (PR-08 unchanged)


async def test_two_guests_are_independent_accounts(client: httpx.AsyncClient, guests_on: None) -> None:
    a = await new_guest(client)
    await answer_first_mcq(client, str(KS_ASSIGN))
    b = await new_guest(client)
    assert a["surveyCode"] != b["surveyCode"] and a["user"]["id"] != b["user"]["id"]
    d = (await client.get(f"/v1/student/assignments/{KS_ASSIGN}")).json()
    assert all(i["result"] is None for i in d["items"])  # B sees none of A's answers
    prog = (await client.get("/v1/student/assignments")).json()["items"][0]
    assert prog.get("answeredCount", 0) == 0


async def test_guest_cannot_reach_teacher_or_admin_routes(client: httpx.AsyncClient, guests_on: None) -> None:
    await new_guest(client)
    for path in ("/v1/lessons", "/v1/classes", "/v1/sources", "/v1/admin/audit-logs", "/v1/admin/survey/export.csv"):
        assert (await client.get(path)).status_code == 403, path
    block = uid("dan-so-vung:blk:q1")
    assert (await client.get(f"/v1/blocks/{block}/provenance")).status_code == 404  # PR-08
    assert (await client.post("/v1/lessons", json={"title": "x", "grade": 10, "sourceRevisionIds": []})).status_code == 403


async def test_guest_code_is_not_a_password_login(client: httpx.AsyncClient, guests_on: None) -> None:
    g = await new_guest(client)
    client.cookies.clear()
    for pw in ("", "!guest", "preclass-demo"):
        r = await login(client, g["surveyCode"], pw)
        assert r.status_code == 401, (pw, r.status_code)  # 401, never 500 from the non-argon2 placeholder


async def test_create_is_rate_limited_per_ip(client: httpx.AsyncClient, guests_on: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUEST_CREATE_PER_HOUR", "2")
    get_settings.cache_clear()
    await new_guest(client)
    await new_guest(client)
    client.cookies.clear()
    r = await client.post("/v1/auth/guest", json={})
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"


async def test_capacity_limit(client: httpx.AsyncClient, guests_on: None, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GUEST_MAX_ACTIVE", "1")
    get_settings.cache_clear()
    await new_guest(client)
    client.cookies.clear()
    r = await client.post("/v1/auth/guest", json={})
    assert r.status_code == 503 and r.json()["code"] == "GUEST_CAPACITY"


async def test_resume_same_guest_and_lockout_on_wrong_codes(client: httpx.AsyncClient, guests_on: None) -> None:
    g = await new_guest(client)
    client.cookies.clear()
    r = await client.post("/v1/auth/guest/resume", json={"surveyCode": g["surveyCode"].lower()})
    assert r.status_code == 200 and r.json()["user"]["id"] == g["user"]["id"]
    assert (await client.get("/v1/me")).json()["surveyCode"] == g["surveyCode"]
    client.cookies.clear()
    for _ in range(5):
        assert (await client.post("/v1/auth/guest/resume", json={"surveyCode": "KS-ZZZZ"})).status_code == 404
    r = await client.post("/v1/auth/guest/resume", json={"surveyCode": g["surveyCode"]})
    assert r.status_code == 429  # even the right code is refused while locked out


async def test_export_has_only_survey_columns(client: httpx.AsyncClient, guests_on: None) -> None:
    g = await new_guest(client)
    await answer_first_mcq(client, str(KS_ASSIGN))
    client.cookies.clear()
    await login(client, "admin@preclass.local")
    r = await client.get("/v1/admin/survey/export.csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().split("\n")
    assert lines[0] == ("survey_code,lesson,item,first_attempt_is_correct,answered_at_utc,"
                        "hints_used,max_hint_level,chat_asks,used_explain,blocked_count,pref_chia_nho,pref_hen_gio_phut,"
                        "pref_bang_so_lieu,pref_giai_thich,pref_nhac_tien_do,focus_mode_used")
    cells = lines[1].split(",")
    assert len(lines) == 2 and cells[0] == g["surveyCode"] and cells[2].startswith("Câu ") and cells[3] in ("true", "false")
    assert g["user"]["id"] not in r.text and "Khách" not in r.text and "@" not in r.text


async def test_class_results_csv_never_shows_a_survey_code(client: httpx.AsyncClient, guests_on: None,
                                                           db: AsyncSession) -> None:
    """The survey code alone logs a guest back in: the class teacher's CSV labels guests Khách 001… instead."""
    first = await new_guest(client)
    await answer_first_mcq(client, str(KS_ASSIGN))
    second = await new_guest(client)
    # One test = one transaction, so now() gave both guests the same created_at: set the joining order explicitly.
    await db.execute(text("UPDATE app_user SET created_at = now() - interval '1 hour' WHERE id = :id"),
                     {"id": first["user"]["id"]})
    client.cookies.clear()
    await login(client, "gv.dia@preclass.local")
    r = await client.get(f"/v1/classes/{uid('class:KS')}/assignments/{KS_ASSIGN}/results.csv")
    assert r.status_code == 200, r.text
    for g in (first, second):
        code = g["surveyCode"]
        assert code not in r.text and code[len("KS-"):] not in r.text and g["user"]["id"] not in r.text
    rows = [line.split(",") for line in r.text.lstrip("﻿").strip().split("\r\n")[1:]]
    assert [row[0] for row in rows] == ["Khách 001", "Khách 002"]  # joining order, not code order
    assert rows[0][1] == "Đang làm" and rows[1][1] == "Chưa làm"


async def test_config_names_the_ai_host_only_when_the_model_is_in_use(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings

    for k, v in (("CHAT_ENABLED", "true"), ("CHAT_MODE", "llm"), ("CHAT_LLM_BASE_URL", "https://api.example.test/openai/v1?key=secret")):
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    try:
        c = (await client.get("/v1/auth/config")).json()
        assert c["chatMode"] == "llm" and c["aiProvider"] == "api.example.test"  # the host only, never the path or a key
        monkeypatch.setenv("CHAT_MODE", "rule")
        get_settings.cache_clear()
        c = (await client.get("/v1/auth/config")).json()
        assert c["chatMode"] == "rule" and c["aiProvider"] is None
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
