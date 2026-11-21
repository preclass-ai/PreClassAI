"""GĐ6: lessons, blocks, provenance, edits + invalidation. AT-03, AT-04, AT-09, AT-08 (see test_source_switch)
and the §10.1 role/IDOR checks for lessons and blocks."""

import uuid

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ids import uid
from tests.conftest import login

pytestmark = pytest.mark.db

L = "san-luong-lua"  # gv.dia, DRAFT, every block AUTO_CHECKED
LREV = uid(f"{L}:lrev")
LOCKED = "dan-so-vung"  # PUBLISHED


def B(k: str, lesson: str = L) -> uuid.UUID:
    return uid(f"{lesson}:blk:{k}")


async def status(db: AsyncSession, k: str, lesson: str = L) -> str:
    return str(await db.scalar(text("SELECT review_status FROM content_block WHERE id=:b"), {"b": B(k, lesson)}))


async def approve(db: AsyncSession, *keys: str, lesson: str = L) -> None:
    for k in keys:
        await db.execute(text(
            "INSERT INTO review_event(block_id, content_hash, reviewer_id, action) "
            "SELECT id, content_hash, (SELECT id FROM app_user WHERE email='gv.dia@preclass.local'), 'APPROVE' "
            "FROM content_block WHERE id=:b"), {"b": B(k, lesson)})
        await db.execute(text("UPDATE content_block SET review_status='APPROVED' WHERE id=:b"), {"b": B(k, lesson)})


async def patch(c: httpx.AsyncClient, k: str, payload: dict, version: int = 1, lesson: str = L) -> httpx.Response:  # type: ignore[type-arg]
    return await c.patch(f"/v1/blocks/{B(k, lesson)}", json={"payload": payload, "version": version})


# ----------------------------------------------------------------------------- reading + roles
async def test_blocks_are_flat_ordered_and_carry_status(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await client.get(f"/v1/revisions/{LREV}/blocks")
    assert r.status_code == 200
    items = r.json()["items"]
    assert [i["position"] for i in items] == sorted(i["position"] for i in items) and len(items) == 18
    q1 = next(i for i in items if i["id"] == str(B("q1")))
    assert q1["kind"] == "worksheet_item" and q1["parentId"] is None and q1["reviewStatus"] == "AUTO_CHECKED"
    assert next(i for i in items if i["id"] == str(B("q1k")))["linkCount"] == 4  # provenance count


async def test_lessons_list_get_history_and_idor(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    mine = (await client.get("/v1/lessons")).json()["items"]
    assert len(mine) == 5 and all(x["authorId"] == str(uid("user:gv.dia")) for x in mine)
    pub = next(x for x in mine if x["title"].startswith("Phân bố dân cư"))
    assert pub["currentRevision"]["state"] == "PUBLISHED" and pub["publishedVersionId"] == str(uid(f"{LOCKED}:published"))
    h = (await client.get(f"/v1/lessons/{uid(f'{L}:lesson')}/history")).json()
    assert h["revisions"][0]["revisionNo"] == 1 and h["revisions"][0]["blockCount"] == 18 and h["events"]
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert [x["title"] for x in (await client.get("/v1/lessons")).json()["items"]] == ["Xuất khẩu hàng hóa chủ lực"]
    for path in (f"/v1/lessons/{uid(f'{L}:lesson')}", f"/v1/lessons/{uid(f'{L}:lesson')}/history",
                 f"/v1/revisions/{LREV}/blocks", f"/v1/blocks/{B('q1')}/provenance"):
        assert (await client.get(path)).status_code == 404, path
    assert (await patch(client, "q1", {"stem": "x", "itemType": "MCQ", "skill": "COMPARE"})).status_code == 404
    assert (await client.delete(f"/v1/blocks/{B('q1')}")).status_code == 404
    assert (await client.put(f"/v1/blocks/{B('q1')}/provenance", json={"noSourceReason": "x", "version": 1})).status_code == 404
    assert (await client.post(f"/v1/revisions/{LREV}/blocks", json={"kind": "paragraph", "payload": {"text": "x"}})).status_code == 404


async def test_students_cannot_touch_lessons_or_blocks(client: httpx.AsyncClient) -> None:
    await login(client, "HS10-01")
    calls = [client.get("/v1/lessons"), client.get(f"/v1/revisions/{LREV}/blocks"),
             patch(client, "q1", {"text": "x"}),
             client.delete(f"/v1/blocks/{B('q1')}"),
             client.post("/v1/lessons", json={"title": "x", "grade": 10, "sourceRevisionIds": [str(uid(f'{L}:srcrev'))]})]
    for coro in calls:
        r = await coro
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"


async def test_student_gets_404_on_provenance(client: httpx.AsyncClient) -> None:
    await login(client, "HS10-01")
    assert (await client.get(f"/v1/blocks/{B('q1')}/provenance")).status_code == 404  # PR-08


async def test_reviewer_reads_only_assigned_lessons_and_never_edits(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "reviewer@preclass.local")
    assert (await client.get(f"/v1/revisions/{LREV}/blocks")).status_code == 404  # not assigned
    await db.execute(text("INSERT INTO lesson_reviewer(lesson_id, reviewer_id) VALUES (:l, :r)"),
                     {"l": uid(f"{L}:lesson"), "r": uid("user:reviewer")})
    assert (await client.get(f"/v1/revisions/{LREV}/blocks")).status_code == 200
    assert (await client.get(f"/v1/blocks/{B('q1')}/provenance")).status_code == 200
    assert [x["id"] for x in (await client.get("/v1/lessons")).json()["items"]] == [str(uid(f"{L}:lesson"))]
    assert (await patch(client, "q1", {"stem": "x", "itemType": "MCQ", "skill": "COMPARE"})).status_code == 403
    assert (await client.put(f"/v1/blocks/{B('q1')}/provenance", json={"noSourceReason": "x", "version": 1})).status_code == 403


async def test_create_lesson_checks_source_visibility(client: httpx.AsyncClient) -> None:
    await login(client, "gv.khac@preclass.local")
    body = {"title": "Bài mới", "grade": 11, "goal": "g"}
    ok = await client.post("/v1/lessons", json={**body, "sourceRevisionIds": [str(uid(f"{LOCKED}:srcrev"))]})  # SCHOOL
    assert ok.status_code == 201, ok.text
    assert ok.json()["currentRevision"]["state"] == "DRAFT" and ok.json()["currentRevision"]["sourceRevisionIds"]
    bad = await client.post("/v1/lessons", json={**body, "sourceRevisionIds": [str(uid(f"{L}:srcrev"))]})  # PRIVATE of dia
    assert bad.status_code == 404
    assert (await client.post("/v1/lessons", json={**body, "sourceRevisionIds": []})).status_code == 422


# ----------------------------------------------------------------------------- AT-09: edit invalidates approval
async def test_at09_editing_an_approved_block_drops_the_approval(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await approve(db, "p1")
    old = await db.scalar(text("SELECT content_hash FROM content_block WHERE id=:b"), {"b": B("p1")})
    await login(client, "gv.dia@preclass.local")
    r = await patch(client, "p1", {"text": "Một câu mới hoàn toàn."})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["reviewStatus"] == "REVIEW_AGAIN" and b["version"] == 2 and b["contentHash"] != old
    assert b["transformation"] == "PARAPHRASED"  # no longer a verbatim ORIGINAL quote
    ev = (await db.execute(text("SELECT before_hash, after_hash, actor_type FROM transformation_event "
                                "WHERE block_id=:b AND operation='EDIT'"), {"b": B("p1")})).one()
    assert (ev[0], ev[1], ev[2]) == (old, b["contentHash"], "TEACHER")
    prov = (await client.get(f"/v1/blocks/{B('p1')}/provenance")).json()
    assert [x["isValid"] for x in prov["reviews"]] == [False]  # the old approval no longer counts


async def test_edit_in_review_state_also_loses_approval(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await approve(db, "p1")
    await db.execute(text("UPDATE lesson_revision SET state='IN_REVIEW' WHERE id=:r"), {"r": LREV})
    await login(client, "gv.dia@preclass.local")
    r = await patch(client, "p1", {"text": "Sửa khi đang duyệt."})
    assert r.status_code == 200 and r.json()["reviewStatus"] == "REVIEW_AGAIN"


# ----------------------------------------------------------------------------- AT-03: dependents + parent
async def test_at03_changing_an_approved_answer_key_reopens_explanation_and_item(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    await approve(db, "q1", "q1k", "q1e", "q2k")
    await login(client, "gv.dia@preclass.local")
    r = await patch(client, "q1k", {"correct": "B"})
    assert r.status_code == 200 and r.json()["reviewStatus"] == "REVIEW_AGAIN"
    assert await status(db, "q1e") == "REVIEW_AGAIN"  # explanation depends on the key
    assert await status(db, "q1") == "REVIEW_AGAIN"  # direct parent (the item)
    assert await status(db, "q2k") == "APPROVED"  # unrelated approvals stay valid
    assert await status(db, "q1o0") == "AUTO_CHECKED"  # untouched, not approved


async def test_editing_a_not_yet_approved_block_needs_revalidation(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await patch(client, "p2", {"text": "Đoạn đã sửa."})
    assert r.status_code == 200 and r.json()["reviewStatus"] == "UNREVIEWED"  # AUTO_CHECKED belonged to the old hash


async def test_noop_patch_changes_nothing(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    cur = (await client.get(f"/v1/revisions/{LREV}/blocks")).json()["items"]
    p2 = next(i for i in cur if i["id"] == str(B("p2")))
    r = await patch(client, "p2", p2["payload"] | {})
    assert r.status_code == 200 and r.json()["version"] == 1 and r.json()["contentHash"] == p2["contentHash"]


# ----------------------------------------------------------------------------- guards
async def test_patch_guards_version_and_payload_shape(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    stale = await patch(client, "p1", {"text": "x"}, version=7)
    assert stale.status_code == 409 and stale.json()["code"] == "VERSION_CONFLICT"
    for payload in ({"nope": 1}, {"text": "x", "extra": 1}, {}, {"text": 5}):
        r = await patch(client, "p1", payload)
        assert r.status_code == 422 and r.json()["code"] in ("PAYLOAD_INVALID", "VALIDATION_ERROR"), payload
    assert (await patch(client, "q1k", {})).status_code == 422  # an answer key needs a shape
    assert (await patch(client, "df", {"label": "x", "value": 1.0})).status_code == 422  # PR-07: unit/period/region


async def test_published_revision_is_frozen(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    pub_rev = uid(f"{LOCKED}:lrev")
    expected = {"code": "REVISION_LOCKED"}
    calls = [
        patch(client, "p1", {"text": "x"}, lesson=LOCKED),
        client.delete(f"/v1/blocks/{B('p1', LOCKED)}"),
        client.post(f"/v1/revisions/{pub_rev}/blocks", json={"kind": "paragraph", "payload": {"text": "x"}}),
        client.put(f"/v1/blocks/{B('p1', LOCKED)}/provenance", json={"noSourceReason": "x", "version": 1}),
    ]
    for coro in calls:
        r = await coro
        assert r.status_code == 409 and r.json()["code"] == expected["code"]
    assert await status(db, "p1", LOCKED) == "APPROVED"


# ----------------------------------------------------------------------------- create / delete
async def test_create_block_with_dependency_and_parent_invalidation(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await approve(db, "q1")
    await login(client, "gv.dia@preclass.local")
    r = await client.post(f"/v1/revisions/{LREV}/blocks", json={
        "kind": "option", "parentId": str(B("q1")), "payload": {"label": "D", "text": "Vùng mới"}})
    assert r.status_code == 201, r.text
    nb = r.json()
    assert nb["transformation"] == "TEACHER_AUTHORED" and nb["reviewStatus"] == "UNREVIEWED"
    assert await db.scalar(text("SELECT kind FROM block_dependency WHERE block_id=:b AND depends_on_block_id=:p"),
                           {"b": nb["id"], "p": B("q1")}) == "LABEL_OF"
    assert await status(db, "q1") == "REVIEW_AGAIN"  # a new child changes the approved parent
    bad = await client.post(f"/v1/revisions/{LREV}/blocks", json={
        "kind": "paragraph", "parentId": str(uuid.uuid4()), "payload": {"text": "x"}})
    assert bad.status_code == 422 and bad.json()["code"] == "PARENT_NOT_FOUND"


async def test_create_block_at_position_shifts_followers(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await client.post(f"/v1/revisions/{LREV}/blocks", json={
        "kind": "paragraph", "position": 2, "payload": {"text": "Chèn vào vị trí 2"}})
    assert r.status_code == 201 and r.json()["position"] == 2
    items = (await client.get(f"/v1/revisions/{LREV}/blocks")).json()["items"]
    assert [i["position"] for i in items] == list(range(1, 20))
    assert items[1]["id"] == r.json()["id"]


async def test_delete_is_soft_cascades_to_children_and_reopens_dependents(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    await approve(db, "q2", "q2e")
    await login(client, "gv.dia@preclass.local")
    assert (await client.delete(f"/v1/blocks/{B('q2k')}")).status_code == 204  # a leaf
    assert await status(db, "q2") == "REVIEW_AGAIN"  # parent of the deleted key
    assert await status(db, "q2e") == "REVIEW_AGAIN"  # its explanation depended on the key
    assert (await client.delete(f"/v1/blocks/{B('q1')}")).status_code == 204  # an item with 7 children
    n = await db.scalar(text("SELECT count(*) FROM content_block WHERE revision_id=:r AND deleted_at IS NOT NULL"),
                        {"r": LREV})
    assert n == 1 + 1 + 4 + 1 + 1  # q2k, q1, its 4 options, key and explanation
    items = (await client.get(f"/v1/revisions/{LREV}/blocks")).json()["items"]
    assert not {str(B(k)) for k in ("q1", "q1o0", "q1k", "q1e", "q2k")} & {i["id"] for i in items}
    assert (await client.delete(f"/v1/blocks/{B('q2k')}")).status_code == 404  # already gone
    assert await db.scalar(text("SELECT count(*) FROM content_block WHERE id=:b"), {"b": B("q1")}) == 1  # soft delete


# ----------------------------------------------------------------------------- provenance (AT-04) + PR-06
async def _anchor_ids(c: httpx.AsyncClient, n: int) -> list[str]:
    items = (await c.get(f"/v1/source-revisions/{uid(f'{L}:srcrev')}/anchors")).json()["items"]
    return [a["id"] for a in items if a["kind"] == "TABLE_CELL"][:n]


async def test_at04_synthesised_block_shows_all_three_sources_and_audits_the_inspection(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    await login(client, "gv.dia@preclass.local")
    nb = (await client.post(f"/v1/revisions/{LREV}/blocks", json={
        "kind": "paragraph", "isFactual": True, "payload": {"text": "Tổng hợp ba ô của bảng."}})).json()
    ids = await _anchor_ids(client, 3)
    put = await client.put(f"/v1/blocks/{nb['id']}/provenance", json={
        "version": nb["version"], "links": [{"anchorId": a, "relation": "derived_from"} for a in ids]})
    assert put.status_code == 200, put.text
    got = (await client.get(f"/v1/blocks/{nb['id']}/provenance")).json()
    assert len(got["links"]) == 3 and {lk["status"] for lk in got["links"]} == {"VERIFIED"}
    assert all(lk["anchor"]["sourceVersion"] == 1 and lk["anchor"]["excerpt"] for lk in got["links"])
    assert got["block"]["linkCount"] == 3 and len(got["events"]) >= 2
    n = await db.scalar(text("SELECT count(*) FROM audit_log WHERE action='INSPECT_PROVENANCE' AND resource_id=:b"),
                        {"b": nb["id"]})
    assert n == 2 and await db.scalar(text("SELECT count(*) FROM audit_log WHERE metadata <> '{}'::jsonb")) == 0  # no content


async def test_provenance_rejects_foreign_anchors_and_bad_shapes(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    other = (await client.get(f"/v1/source-revisions/{uid('dien-tich-rung:srcrev')}/anchors")).json()["items"][0]["id"]
    r = await client.put(f"/v1/blocks/{B('p1')}/provenance", json={"version": 1, "links": [
        {"anchorId": other, "relation": "quotes"}]})
    assert r.status_code == 422 and r.json()["code"] == "ANCHOR_NOT_IN_LESSON"  # PR-06: server verifies
    r = await client.put(f"/v1/blocks/{B('p1')}/provenance", json={"version": 1, "links": [
        {"anchorId": str(uuid.uuid4()), "relation": "quotes"}]})
    assert r.status_code == 422 and r.json()["code"] == "ANCHOR_NOT_IN_LESSON"
    both = await client.put(f"/v1/blocks/{B('p1')}/provenance", json={"version": 1, "links": [], "noSourceReason": "x"})
    assert both.status_code == 422 and both.json()["code"] == "PROVENANCE_INVALID"
    neither = await client.put(f"/v1/blocks/{B('p1')}/provenance", json={"version": 1})
    assert neither.status_code == 422


async def test_no_source_reason_replaces_links_and_changes_the_hash(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await approve(db, "q1k", "q1e")
    old = await db.scalar(text("SELECT content_hash FROM content_block WHERE id=:b"), {"b": B("q1k")})
    await login(client, "gv.dia@preclass.local")
    r = await client.put(f"/v1/blocks/{B('q1k')}/provenance", json={"version": 1, "noSourceReason": "Câu hỏi sư phạm"})
    assert r.status_code == 200
    blk = r.json()["block"]
    assert blk["noSourceReason"] == "Câu hỏi sư phạm" and blk["linkCount"] == 0 and blk["contentHash"] != old
    assert blk["reviewStatus"] == "REVIEW_AGAIN" and await status(db, "q1e") == "REVIEW_AGAIN"
