"""Lesson plan upload, the check screen data, teacher confirmation, the pre-class lesson draft, and who may see it."""

import json

import httpx
import pytest

from tests.conftest import login
from tests.plan_fixtures import font_path, plan_docx, plan_pdf

pytestmark = pytest.mark.db
H = {"X-PreClass-CSRF": "1"}


async def upload(c: httpx.AsyncClient, data: bytes, name: str = "plan.docx") -> list[dict]:
    r = await c.post("/v1/lesson-plans", files={"file": (name, data)}, headers=H)
    assert r.status_code == 202, r.text
    job = (await c.get(f"/v1/lesson-plans/jobs/{r.json()['id']}")).json()
    assert job["state"] == "done", job  # the test runner runs the job inline
    return [(await c.get(f"/v1/lesson-plans/{i}")).json() for i in job["planIds"]]


async def test_upload_read_confirm_and_build_a_draft_lesson(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    (p,) = await upload(client, plan_docx())
    assert p["title"] == "CHỦ ĐỀ MẪU" and p["subject"] == "DIA_LI" and p["ppctPeriod"] == "7"
    assert sorted(p["activities"]) == ["hinh_thanh", "luyen_tap", "mo_dau", "van_dung"]
    assert p["mcqCount"] == 2 and p["needsConfirmationCount"] == 1 and p["lessonId"] is None
    assert p["suggestedDueAt"].startswith("2026-09-21T16:59")  # 21/09 23:59 Vietnam time (UTC+7)
    d = (await client.get(f"/v1/lesson-plans/{p['id']}")).json()
    assert [q["correctOption"] for q in d["mcqs"]] == ["B", None] and d["mcqs"][0]["answerSource"] == "docx_underline"
    assert "Phạm Văn Thử" not in json.dumps(d, ensure_ascii=False)  # signature block removed
    assert {o["competencyCode"] for o in d["objectives"]} == {"NHAN_THUC"}

    unconfirmed = d["mcqs"][1]
    bad = await client.put(f"/v1/lesson-plans/{p['id']}/mcqs/{unconfirmed['id']}/answer", json={"correctOption": "D"}, headers=H)
    assert bad.status_code == 200 and bad.json()["mcqs"][1]["answerSource"] == "teacher"
    assert bad.json()["needsConfirmationCount"] == 0

    r = await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["practiceItems"] == 2 and out["skippedUnconfirmed"] == 0 and out["blocks"] >= 12
    assert (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).status_code == 409
    assert (await client.get(f"/v1/lesson-plans/{p['id']}")).json()["lessonId"] == out["lessonId"]

    lesson = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()
    blocks = (await client.get(f"/v1/revisions/{lesson['currentRevision']['id']}/blocks")).json()["items"]
    assert blocks and all(b["reviewStatus"] != "APPROVED" for b in blocks)  # a draft: nothing approved by the import
    assert lesson["currentRevision"]["state"] == "DRAFT"


async def test_unconfirmed_answers_are_skipped_not_guessed(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    (p,) = await upload(client, plan_docx())
    out = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()
    assert out["practiceItems"] == 1 and out["skippedUnconfirmed"] == 1


@pytest.mark.skipif(font_path() is None, reason="no font with Vietnamese glyphs")
async def test_pdf_with_two_lessons_gives_knowledge_cards(client: httpx.AsyncClient) -> None:
    assert (font := font_path())
    await login(client, "gv.dia@preclass.local")
    plans = await upload(client, plan_pdf(font), "plan.pdf")
    assert [x["title"] for x in plans] == ["DÂN CƯ MẪU", "ĐÔ THỊ MẪU"]
    assert plans[0]["suggestedDueAt"].startswith("2026-09-07T16:59")
    first = plans[0]["id"]
    for q in (await client.get(f"/v1/lesson-plans/{first}")).json()["mcqs"]:
        if q["needsConfirmation"]:
            await client.put(f"/v1/lesson-plans/{first}/mcqs/{q['id']}/answer", json={"correctOption": "A"}, headers=H)
    out = (await client.post(f"/v1/lesson-plans/{first}/lesson", headers=H)).json()
    assert out["practiceItems"] == 4 and out["leftForAfterClass"] == 0
    lesson = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()
    blocks = (await client.get(f"/v1/revisions/{lesson['currentRevision']['id']}/blocks")).json()["items"]
    kinds = [b["kind"] for b in blocks]
    assert kinds.count("paragraph") == 1 and "card_front" in kinds and "card_back" in kinds  # the knowledge box, quoted


async def test_only_the_owner_teacher_sees_a_plan(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    (p,) = await upload(client, plan_docx())
    client.cookies.clear()
    await login(client, "HS10-01")
    assert (await client.get(f"/v1/lesson-plans/{p['id']}")).status_code == 403
    assert (await client.post("/v1/lesson-plans", files={"file": ("a.docx", plan_docx())}, headers=H)).status_code == 403
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert (await client.get(f"/v1/lesson-plans/{p['id']}")).status_code == 404
    assert (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).status_code == 404
    assert (await client.get("/v1/lesson-plans")).json()["items"] == []


async def test_a_file_that_is_not_a_plan_is_refused(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await client.post("/v1/lesson-plans", files={"file": ("a.txt", b"hello")}, headers=H)
    assert r.status_code == 422


async def test_a_reading_error_arrives_in_the_job_not_as_a_crash(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await client.post("/v1/lesson-plans", files={"file": ("a.pdf", b"%PDF-1.4\n% not a real pdf")}, headers=H)
    assert r.status_code == 202, r.text
    job = (await client.get(f"/v1/lesson-plans/jobs/{r.json()['id']}")).json()
    assert job["state"] == "failed" and job["errorTitle"] and job["planIds"] == []
    assert (await client.get("/v1/lesson-plans/jobs/latest")).json()["job"]["id"] == job["id"]
    # a failed job does not block the next upload
    assert (await client.post("/v1/lesson-plans", files={"file": ("p.docx", plan_docx())}, headers=H)).status_code == 202


async def test_one_active_job_per_teacher_and_jobs_are_private(client: httpx.AsyncClient, db) -> None:  # noqa: ANN001
    from sqlalchemy import update

    from app.db import models as m

    await login(client, "gv.dia@preclass.local")
    r = await client.post("/v1/lesson-plans", files={"file": ("p.docx", plan_docx())}, headers=H)
    job_id = r.json()["id"]
    await db.execute(update(m.LessonPlanJob).where(m.LessonPlanJob.id == job_id).values(state="parsing"))
    busy = await client.post("/v1/lesson-plans", files={"file": ("p.docx", plan_docx())}, headers=H)
    assert busy.status_code == 409 and busy.json()["code"] == "PARSE_BUSY"
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert (await client.get(f"/v1/lesson-plans/jobs/{job_id}")).status_code == 404
    assert (await client.get("/v1/lesson-plans/jobs/latest")).json()["job"] is None


async def test_competency_defaults_flow_to_blocks_and_the_teacher_can_change_it(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    (p,) = await upload(client, plan_docx())
    d = (await client.get(f"/v1/lesson-plans/{p['id']}")).json()
    assert [c["code"] for c in d["competencies"]] == ["NHAN_THUC", "TIM_HIEU", "VAN_DUNG"]
    assert all(q["competencyCode"] in ("NHAN_THUC", "TIM_HIEU") for q in d["mcqs"])
    q0 = d["mcqs"][0]
    r = await client.put(f"/v1/lesson-plans/{p['id']}/mcqs/{q0['id']}/competency", json={"competencyCode": "TIM_HIEU"}, headers=H)
    assert r.status_code == 200 and r.json()["mcqs"][0]["competencyCode"] == "TIM_HIEU"
    bad = await client.put(f"/v1/lesson-plans/{p['id']}/mcqs/{q0['id']}/competency", json={"competencyCode": "NOPE"}, headers=H)
    assert bad.status_code == 422 and bad.json()["code"] == "INVALID_COMPETENCY"
    out = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()
    rev = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()["currentRevision"]["id"]
    items = (await client.get(f"/v1/revisions/{rev}/blocks")).json()["items"]
    item = next(b for b in items if b["kind"] == "worksheet_item")
    assert item["competencyCode"] == "TIM_HIEU"  # the teacher's choice
    first = next(b for b in items if b["kind"] == "instruction")
    assert first["competencyCode"] in ("NHAN_THUC", "VAN_DUNG")  # default from the activity
    r = await client.put(f"/v1/blocks/{item['id']}/competency", json={"competencyCode": "VAN_DUNG"}, headers=H)
    assert r.status_code == 200 and r.json()["competencyCode"] == "VAN_DUNG" and r.json()["reviewStatus"] == item["reviewStatus"]


async def test_assign_takes_a_teach_date_and_fills_the_due_date(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    (p,) = await upload(client, plan_docx())
    out = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()
    lesson = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()
    assert lesson["teachDate"] == p["taughtFrom"]  # the assign form pre-fills the learning day from the plan
