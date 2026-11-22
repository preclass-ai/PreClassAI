"""Teacher: change the due time, cancel an assignment, see where a lesson is assigned. Student: "Làm lại" (practice) keeps the first attempt."""

import csv
import io
from datetime import UTC, datetime, timedelta

import httpx
import pytest

from tests.conftest import login
from tests.integration.test_student import ASSIGN, CLASS, attempt, detail

pytestmark = pytest.mark.db
A_URL = f"/v1/classes/{CLASS}/assignments/{ASSIGN}"


async def test_practice_needs_a_first_attempt_and_never_changes_the_results(client: httpx.AsyncClient) -> None:
    d = await detail(client)
    it = next(i for i in d["items"] if i["itemType"] == "MCQ")
    url = f"/v1/student/assignments/{ASSIGN}/practice"
    redo = {"itemId": it["id"], "answer": {"choice": "A"}}
    assert (await client.post(url, json=redo)).status_code == 409  # practice only after the first attempt
    first = (await attempt(client, it["id"], {"choice": "A"})).json()
    again = await client.post(url, json={"itemId": it["id"], "answer": {"choice": "B"}})
    assert again.status_code == 201 and isinstance(again.json()["isCorrect"], bool) and again.json()["explanation"]
    assert (await client.post(url, json={"itemId": it["id"], "answer": {"choice": "B"}})).status_code == 201  # as often as they like
    kept = next(i for i in (await client.get(f"/v1/student/assignments/{ASSIGN}")).json()["items"] if i["id"] == it["id"])
    assert kept["result"]["isCorrect"] == first["isCorrect"]  # the first attempt is the one that counts
    await login(client, "gv.dia@preclass.local")
    prog = {i["itemBlockId"]: i for i in (await client.get(f"{A_URL}/progress")).json()["items"]}
    assert prog[it["id"]]["answeredCount"] == 1  # insights and progress still see one attempt
    rows = list(csv.reader(io.StringIO((await client.get(f"{A_URL}/results.csv")).content.decode("utf-8").lstrip("﻿"))))
    me = next(r for r in rows[1:] if r[0] == "HS10-01")
    col = 9 + 4 * [i["id"] for i in d["items"]].index(it["id"])
    assert rows[0][col + 3].endswith("Số lần làm lại") and me[col + 3] == "2" and me[6] == "2"


async def test_teacher_changes_the_due_time_and_cancels(client: httpx.AsyncClient) -> None:
    await detail(client)
    await login(client, "gv.dia@preclass.local")
    lesson = (await client.get(f"/v1/classes/{CLASS}/assignments")).json()["items"][0]["lessonId"]
    shown = (await client.get(f"/v1/lessons/{lesson}/assignments")).json()["items"]
    assert any(x["id"] == str(ASSIGN) and x["classCode"] == "10A1" for x in shown)  # "Đã giao cho: 10A1 (hạn …)"
    new_due = (datetime.now(UTC) + timedelta(days=9)).replace(microsecond=0)
    r = await client.patch(A_URL, json={"dueAt": new_due.isoformat()})
    assert r.status_code == 200 and datetime.fromisoformat(r.json()["dueAt"]) == new_due
    assert (await client.patch(A_URL, json={"dueAt": "2000-01-01T00:00:00+00:00"})).status_code == 422  # before it opens
    await login(client, "gv.khac@preclass.local")
    assert (await client.patch(A_URL, json={"dueAt": new_due.isoformat()})).status_code == 404  # not their class
    assert (await client.delete(A_URL)).status_code == 404
    await login(client, "gv.dia@preclass.local")
    assert (await client.delete(A_URL)).status_code == 204
    assert all(x["id"] != str(ASSIGN) for x in (await client.get(f"/v1/classes/{CLASS}/assignments")).json()["items"])
    assert (await client.delete(A_URL)).status_code == 404
    await login(client, "HS10-01")
    assert (await client.get(f"/v1/student/assignments/{ASSIGN}")).status_code == 404  # students no longer see it
    assert all(i["id"] != str(ASSIGN) for i in (await client.get("/v1/student/assignments")).json()["items"])
