"""GĐ7: generation (MockProvider) + validation VAL-01..09. AT-01, AT-02, AT-05, AT-06 and the AI kill switch."""

import io
import uuid

import asyncpg
import httpx
import pytest
from docx import Document
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.generation import recover_after_restart
from app.ids import uid
from tests.conftest import PG_URL, login

pytestmark = pytest.mark.db

DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
ROWS = [("Đồng bằng sông Hồng", "23,2"), ("Tây Nguyên", "5,9"), ("Đông Nam Bộ", "17,8"), ("Duyên hải miền Trung", "9,4")]


def docx_table() -> bytes:
    d = Document()
    d.add_heading("Số dân các vùng năm 2020 (DỮ LIỆU MINH HỌA)", level=1)
    d.add_paragraph("Dân cư nước ta phân bố không đều giữa các vùng kinh tế.")
    d.add_paragraph("Vùng đồng bằng có điều kiện sản xuất thuận lợi hơn.")
    t = d.add_table(rows=1 + len(ROWS), cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Vùng", "Số dân (triệu người)"
    for i, (a, b) in enumerate(ROWS, 1):
        t.cell(i, 0).text, t.cell(i, 1).text = a, b
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


async def new_lesson(c: httpx.AsyncClient) -> tuple[str, str]:
    """-> (lesson id, revision id) with a DOCX source containing a table."""
    src = (await c.post("/v1/sources/docx", files={"file": ("a.docx", docx_table(), DOCX_CT)},
                        data={"title": "Bảng dân số"})).json()
    lesson = (await c.post("/v1/lessons", json={"title": "Bài thử", "grade": 10,
                                                "sourceRevisionIds": [src["latestRevision"]["id"]]})).json()
    return lesson["id"], lesson["currentRevision"]["id"]


async def generate(c: httpx.AsyncClient, lesson: str, **body: object) -> httpx.Response:
    return await c.post(f"/v1/lessons/{lesson}/generate", json={"outputType": "WORKSHEET", "nItems": 4, **body})


async def blocks(c: httpx.AsyncClient, rev: str) -> list[dict]:  # type: ignore[type-arg]
    return (await c.get(f"/v1/revisions/{rev}/blocks")).json()["items"]  # type: ignore[no-any-return]


async def failed_rules(c: httpx.AsyncClient, block_id: str) -> dict[str, dict]:  # type: ignore[type-arg]
    prov = (await c.get(f"/v1/blocks/{block_id}/provenance")).json()
    return {v["rule"]: v["evidence"] for v in prov["validations"] if v["outcome"] == "FAIL" and v["isCurrent"]}


# ----------------------------------------------------------------------------- happy path
async def test_generate_worksheet_creates_checked_unapproved_blocks(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    r = await generate(client, lesson)
    assert r.status_code == 202, r.text
    job = (await client.get(f"/v1/jobs/{r.json()['jobId']}")).json()
    assert job["status"] == "SUCCEEDED" and job["model"] == "mock-v1" and job["blockCount"] > 10 and job["error"] is None
    items = await blocks(client, rev)
    assert len(items) == job["blockCount"]
    assert {i["reviewStatus"] for i in items} == {"AUTO_CHECKED"}  # PR-02: AI never approves; a clean draft is only checked
    assert {"heading", "paragraph", "data_fact", "worksheet_item", "option", "answer_key", "explanation"} <= {i["kind"] for i in items}
    ev = await db.scalars(text("SELECT DISTINCT generator_version FROM transformation_event e JOIN content_block b ON b.id=e.block_id "
                               "WHERE b.revision_id=:r AND e.operation='GENERATE'").bindparams(r=uuid.UUID(rev)))
    assert list(ev) == ["mock-v1/v1"]
    assert await db.scalar(text("SELECT count(*) FROM provenance_link l JOIN content_block b ON b.id=l.block_id WHERE b.revision_id=:r"),
                           {"r": uuid.UUID(rev)}) > 10
    assert await db.scalar(text("SELECT sum(tokens) FROM usage_daily")) > 0
    numeric_key = next(i for i in items if i["kind"] == "answer_key" and "derivation" in i["payload"] and i["payload"]["derivation"])
    assert numeric_key["reviewStatus"] == "AUTO_CHECKED"  # the derived number was recomputed and matched


async def test_flashcards(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    r = await client.post(f"/v1/lessons/{lesson}/generate", json={"outputType": "FLASHCARDS", "nItems": 3})
    assert r.status_code == 202
    kinds = [i["kind"] for i in await blocks(client, rev)]
    assert kinds == ["card_front", "card_back"] * 3


# ----------------------------------------------------------------------------- guards
async def test_ai_kill_switch_and_budget(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, _ = await new_lesson(client)
    monkeypatch.setattr(get_settings(), "ai_enabled", False)
    r = await generate(client, lesson)
    assert r.status_code == 503 and r.json()["code"] == "AI_DISABLED"
    assert (await client.get("/v1/lessons")).status_code == 200  # everything else keeps working (PR-10)
    monkeypatch.setattr(get_settings(), "ai_enabled", True)
    monkeypatch.setattr(get_settings(), "generation_daily_token_budget", 0)
    assert (await generate(client, lesson)).json()["code"] == "AI_DISABLED"


async def test_one_job_per_revision_and_non_empty_revisions(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    await db.execute(text("INSERT INTO generation_job(revision_id, output_type, status) VALUES (:r, 'WORKSHEET', 'RUNNING')"),
                     {"r": uuid.UUID(rev)})
    busy = await generate(client, lesson)
    assert busy.status_code == 409 and busy.json()["code"] == "JOB_ALREADY_RUNNING"
    await db.execute(text("UPDATE generation_job SET status='FAILED'"))
    assert (await generate(client, lesson)).status_code == 202
    again = await generate(client, lesson)
    assert again.status_code == 409 and again.json()["code"] == "REVISION_NOT_EMPTY"
    n = len(await blocks(client, rev))
    assert (await generate(client, lesson, mode="append")).status_code == 202
    assert len(await blocks(client, rev)) > n  # append keeps the existing blocks


async def test_generate_roles_and_idor(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, _ = await new_lesson(client)
    job = (await generate(client, lesson)).json()["jobId"]
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert (await generate(client, lesson)).status_code == 404
    assert (await client.get(f"/v1/jobs/{job}")).status_code == 404
    client.cookies.clear()
    await login(client, "HS10-01")
    assert (await generate(client, lesson)).status_code == 403
    assert (await client.get(f"/v1/jobs/{job}")).status_code == 403
    client.cookies.clear()
    assert (await generate(client, lesson)).status_code == 401


async def test_generate_on_published_lesson_is_locked(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await generate(client, str(uid("dan-so-vung:lesson")))
    assert r.status_code == 409 and r.json()["code"] == "REVISION_LOCKED"


async def test_restart_marks_running_jobs_failed() -> None:
    conn = await asyncpg.connect(PG_URL)
    jid = uuid.uuid4()
    try:
        await conn.execute("INSERT INTO generation_job(id, revision_id, output_type, status) VALUES ($1,$2,'WORKSHEET','RUNNING')",
                           jid, uid("gdp-nganh:lrev"))
        assert await recover_after_restart() >= 1
        row = await conn.fetchrow("SELECT status, error FROM generation_job WHERE id=$1", jid)
        assert (row["status"], row["error"]) == ("FAILED", "restart")
    finally:
        await conn.execute("DELETE FROM generation_job WHERE id=$1", jid)
        await conn.close()


# ----------------------------------------------------------------------------- faults injected by the mock
async def _inject(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch, flag: str) -> list[dict]:  # type: ignore[type-arg]
    monkeypatch.setattr(get_settings(), "mock_inject", flag)
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    assert (await generate(client, lesson)).status_code == 202
    return await blocks(client, rev)


async def test_at01_changed_diacritic_in_a_quote_is_a_blocker_with_position(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = await _inject(client, monkeypatch, "changed_quote")
    quote = next(i for i in items if i["kind"] == "paragraph")
    assert quote["reviewStatus"] == "FLAGGED" and quote["blockerCount"] >= 1
    ev = (await failed_rules(client, quote["id"]))["VAL-02"]
    assert isinstance(ev["position"], int) and ev["anchor"].startswith("anc_")
    others = [i for i in items if i["kind"] == "paragraph" and i["id"] != quote["id"]]
    assert all(o["reviewStatus"] == "AUTO_CHECKED" for o in others)  # exact quotes still pass (diacritics preserved)


async def test_at02_unknown_anchor_is_dropped_logged_and_block_flagged(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = await _inject(client, monkeypatch, "fake_anchor")
    fact = next(i for i in items if i["kind"] == "data_fact")
    assert fact["linkCount"] == 0 and fact["reviewStatus"] == "FLAGGED"  # the invented id never became a link
    rules = await failed_rules(client, fact["id"])
    assert rules["VAL-03"]["reason"] == "no_verified_source_and_no_reason" and rules["VAL-01"]["droppedAnchors"] == 1


async def test_at06_number_not_in_the_source_is_a_blocker(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    items = await _inject(client, monkeypatch, "new_number")
    bad = [i for i in items if i["kind"] == "explanation" and i["reviewStatus"] == "FLAGGED"]
    assert len(bad) == 1
    assert (await failed_rules(client, bad[0]["id"]))["VAL-03"]["numbersNotInSources"] == [77.7]
    assert next(i for i in items if i["id"] == bad[0]["parentId"])["reviewStatus"] == "AUTO_CHECKED"  # only that block


async def test_two_answer_keys_flag_the_item(client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch) -> None:
    items = await _inject(client, monkeypatch, "two_keys")
    flagged = [i for i in items if i["kind"] == "worksheet_item" and i["reviewStatus"] == "FLAGGED"]
    assert len(flagged) == 1
    assert (await failed_rules(client, flagged[0]["id"]))["VAL-04"] == {"reason": "answer_keys", "count": 2}


# ----------------------------------------------------------------------------- validate endpoint
async def test_at05_ai_proposed_without_source_needs_a_reason_but_still_needs_review(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    await generate(client, lesson)
    stem = next(i for i in await blocks(client, rev) if i["kind"] == "worksheet_item")
    assert stem["reviewStatus"] == "AUTO_CHECKED" and stem["noSourceReason"]  # has a reason: checked, NOT approved
    await db.execute(text("UPDATE content_block SET no_source_reason = NULL WHERE id=:b"), {"b": stem["id"]})
    out = (await client.post(f"/v1/revisions/{rev}/validate")).json()
    assert {"blockId": stem["id"], "reviewStatus": "FLAGGED", "failedRules": ["VAL-03"]} in [
        {"blockId": b["blockId"], "reviewStatus": b["reviewStatus"], "failedRules": b["failedRules"]} for b in out["blocks"]]
    assert out["blockerCount"] >= 1


async def test_wrong_derived_number_is_caught_after_an_edit(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    await generate(client, lesson)
    key = next(i for i in await blocks(client, rev) if i["kind"] == "answer_key" and i["payload"].get("derivation"))
    payload = {**key["payload"], "value": 99.0}
    assert (await client.patch(f"/v1/blocks/{key['id']}", json={"payload": payload, "version": key["version"]})).status_code == 200
    out = (await client.post(f"/v1/revisions/{rev}/validate")).json()
    hit = next(b for b in out["blocks"] if b["blockId"] == key["id"])
    assert hit["reviewStatus"] == "FLAGGED" and "VAL-03" in hit["failedRules"]


async def test_validate_seeded_draft_is_idempotent_and_keeps_valid_approvals(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    rev = uid("dien-tich-rung:lrev")
    first = (await client.post(f"/v1/revisions/{rev}/validate")).json()
    flagged = {b["blockId"]: b for b in first["blocks"]}
    assert str(uid("dien-tich-rung:blk:q1e")) in flagged and flagged[str(uid("dien-tich-rung:blk:q1e"))]["failedRules"] == ["VAL-03"]
    approved = str(uid("dien-tich-rung:blk:h"))
    assert approved not in flagged  # a valid approval stays APPROVED (VAL-06 passes)
    n = await db.scalar(text("SELECT count(*) FROM validation_result"))
    again = (await client.post(f"/v1/revisions/{rev}/validate")).json()
    assert again["blockerCount"] == first["blockerCount"]
    assert await db.scalar(text("SELECT count(*) FROM validation_result")) == n  # no duplicate rows


async def test_val06_approval_that_no_longer_matches_its_sources_reopens_the_block(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    await login(client, "gv.dia@preclass.local")
    rev, h = uid("dien-tich-rung:lrev"), uid("dien-tich-rung:blk:h")
    await db.execute(text("DELETE FROM provenance_link WHERE block_id=:b"), {"b": h})  # sources changed behind the approval
    out = (await client.post(f"/v1/revisions/{rev}/validate")).json()
    hit = next(b for b in out["blocks"] if b["blockId"] == str(h))
    assert hit["reviewStatus"] == "REVIEW_AGAIN" and "VAL-06" in hit["failedRules"]


async def test_validate_guards(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    locked = await client.post(f"/v1/revisions/{uid('dan-so-vung:lrev')}/validate")
    assert locked.status_code == 409 and locked.json()["code"] == "REVISION_LOCKED"
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert (await client.post(f"/v1/revisions/{uid('dien-tich-rung:lrev')}/validate")).status_code == 404
    client.cookies.clear()
    await login(client, "HS10-01")
    assert (await client.post(f"/v1/revisions/{uid('dien-tich-rung:lrev')}/validate")).status_code == 403
