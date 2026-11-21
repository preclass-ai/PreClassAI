"""GĐ9: student API, attempts, progress. AT-12 (student side), AT-13, PR-08, IDOR/role."""

import json
import uuid
from typing import Any

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ids import uid
from tests.conftest import login

pytestmark = pytest.mark.db

ASSIGN = uid("dan-so-vung:assignment")
PUB = uid("dan-so-vung:published")
CLASS = uid("class:10A1")
FORBIDDEN_KEYS = {"correct", "rubricPoints", "derivation", "tolerance", "provenance", "reviewStatus", "contentHash",
                  "sourceHashes", "validation", "answerKey", "links", "noSourceReason", "withdrawReason"}


def keys(o: object) -> set[str]:
    if isinstance(o, dict):
        return set(o) | {k for v in o.values() for k in keys(v)}
    if isinstance(o, list):
        return {k for v in o for k in keys(v)}
    return set()


async def detail(c: httpx.AsyncClient, user: str = "HS10-01") -> dict[str, Any]:
    await login(c, user)
    r = await c.get(f"/v1/student/assignments/{ASSIGN}")
    assert r.status_code == 200, r.text
    return dict(r.json())


async def attempt(c: httpx.AsyncClient, item: object, answer: dict[str, Any], rid: object = None) -> httpx.Response:
    return await c.post(f"/v1/student/assignments/{ASSIGN}/attempts",
                        json={"itemId": str(item), "answer": answer, "requestId": str(rid or uuid.uuid4())})


async def test_pr08_student_dto_has_no_answers_or_internals(client: httpx.AsyncClient) -> None:
    d = await detail(client)
    assert d["items"] and not (keys(d) & FORBIDDEN_KEYS), keys(d) & FORBIDDEN_KEYS
    assert all(i["result"] is None for i in d["items"])  # no explanation before answering
    assert "answer_key" not in json.dumps(d)


async def test_at13_student_answers_then_sees_result_and_explanation(client: httpx.AsyncClient) -> None:
    d = await detail(client)
    mcq = next(i for i in d["items"] if i["itemType"] == "MCQ")
    r = await attempt(client, mcq["id"], {"choice": "A"})
    assert r.status_code == 201
    res = r.json()
    assert res["itemId"] == mcq["id"] and isinstance(res["isCorrect"], bool) and res["explanation"]
    after = (await client.get(f"/v1/student/assignments/{ASSIGN}")).json()
    assert next(i for i in after["items"] if i["id"] == mcq["id"])["result"]["explanation"] == res["explanation"]
    lst = (await client.get("/v1/student/assignments")).json()["items"]
    assert lst[0]["answeredCount"] == 1 and lst[0]["status"] == "IN_PROGRESS"


async def test_one_attempt_per_item_and_idempotent_request_id(client: httpx.AsyncClient, db: AsyncSession) -> None:
    d = await detail(client)
    item = d["items"][0]["id"]
    rid = uuid.uuid4()
    first = await attempt(client, item, {"choice": "B"}, rid)
    again = await attempt(client, item, {"choice": "B"}, rid)
    assert first.status_code == 201 and again.status_code == 201 and again.json() == first.json()
    other = await attempt(client, item, {"choice": "A"})
    assert other.status_code == 409 and other.json()["code"] == "ALREADY_ANSWERED"
    assert await db.scalar(text("SELECT count(*) FROM student_attempt")) == 1


async def test_grading_by_item_type(client: httpx.AsyncClient) -> None:
    d = await detail(client)
    for it in d["items"]:
        ans = ({"choice": "A"} if it["itemType"] == "MCQ" else {"value": 0.0} if it["itemType"] == "NUMERIC"
               else {"text": "câu trả lời"})
        r = await attempt(client, it["id"], ans)
        assert r.status_code == 201, r.text
        if it["itemType"] == "SHORT":
            assert r.json()["isCorrect"] is None


async def test_unknown_item_is_404(client: httpx.AsyncClient) -> None:
    await detail(client)
    assert (await attempt(client, uuid.uuid4(), {"choice": "A"})).status_code == 404


async def test_idor_and_roles(client: httpx.AsyncClient) -> None:
    await login(client, "HS11-01")  # other class → 404, not 403
    assert (await client.get(f"/v1/student/assignments/{ASSIGN}")).status_code == 404
    assert (await attempt(client, uid("dan-so-vung:blk:q1"), {"choice": "A"})).status_code == 404
    assert (await client.get("/v1/student/assignments")).json()["items"] == []
    for who in ("gv.dia@preclass.local", "admin@preclass.local"):  # staff on student endpoints → 403
        await login(client, who)
        assert (await client.get("/v1/student/assignments")).status_code == 403
        assert (await client.get(f"/v1/student/assignments/{ASSIGN}")).status_code == 403
    await login(client, "HS10-01")  # student on teacher endpoints → 403
    assert (await client.get(f"/v1/classes/{CLASS}/assignments/{ASSIGN}/progress")).status_code == 403
    assert (await client.get(f"/v1/classes/{CLASS}/assignments")).status_code == 403
    d = await detail(client, "HS10-01")  # attempts are per student
    item = d["items"][0]["id"]
    assert (await attempt(client, item, {"choice": "A"})).status_code == 201
    other = await detail(client, "HS10-02")
    assert all(i["result"] is None for i in other["items"])
    assert (await attempt(client, item, {"choice": "B"})).status_code == 201


async def test_window_open_closed_and_withdrawn(client: httpx.AsyncClient, db: AsyncSession) -> None:
    d = await detail(client)
    item = d["items"][0]["id"]
    await db.execute(text("UPDATE assignment SET open_at = now() + interval '1 day' WHERE id=:a"), {"a": ASSIGN})
    assert (await client.get(f"/v1/student/assignments/{ASSIGN}")).status_code == 404  # before openAt
    assert (await client.get("/v1/student/assignments")).json()["items"] == []
    await db.execute(text("UPDATE assignment SET open_at = now() - interval '2 day', due_at = now() - interval '1 day' "
                          "WHERE id=:a"), {"a": ASSIGN})
    assert (await client.get(f"/v1/student/assignments/{ASSIGN}")).status_code == 200
    closed = await attempt(client, item, {"choice": "A"})
    assert closed.status_code == 409 and closed.json()["code"] == "PAST_DUE"
    assert (await client.get("/v1/student/assignments")).json()["items"][0]["status"] == "CLOSED"
    await db.execute(text("UPDATE published_version SET state='WITHDRAWN' WHERE id=:p"), {"p": PUB})
    for r in (await client.get(f"/v1/student/assignments/{ASSIGN}"), await attempt(client, item, {"choice": "A"})):
        assert r.status_code == 410 and r.json()["code"] == "WITHDRAWN"  # AT-12 student side


async def test_progress_for_teacher_of_that_class_only(client: httpx.AsyncClient) -> None:
    d = await detail(client)
    mcq = next(i for i in d["items"] if i["itemType"] == "MCQ")
    await attempt(client, mcq["id"], {"choice": "A"})
    await login(client, "HS10-02")
    await attempt(client, mcq["id"], {"choice": "B"})
    await login(client, "gv.dia@preclass.local")
    p = await client.get(f"/v1/classes/{CLASS}/assignments/{ASSIGN}/progress")
    assert p.status_code == 200
    body = p.json()
    row = next(i for i in body["items"] if i["itemBlockId"] == mcq["id"])
    assert body["studentCount"] == 15 and row["answeredCount"] == 2 and row["firstAttemptCorrectRate"] in (0.0, 0.5, 1.0)
    assert not (keys(body) & {"studentId", "displayName", "answer"})  # aggregate only
    await login(client, "gv.khac@preclass.local")  # teacher outside the class
    assert (await client.get(f"/v1/classes/{CLASS}/assignments/{ASSIGN}/progress")).status_code == 404
    await login(client, "gv.dia@preclass.local")
    wrong = await client.get(f"/v1/classes/{uid('class:11A1')}/assignments/{ASSIGN}/progress")
    assert wrong.status_code == 404  # assignment is not in that class
