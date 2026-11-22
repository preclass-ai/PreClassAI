"""GĐ8: hash-bound review, queue, publish gate, snapshot, new revision, withdraw, assignments.
AT-10, AT-11, AT-12 (teacher side), AT-14."""

import uuid

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.hashing import canonical_json, sha256_hex
from app.ids import uid
from tests.conftest import login
from tests.integration.test_generation import blocks, generate, new_lesson

pytestmark = pytest.mark.db

SEED = "san-luong-lua"  # gv.dia draft, every block AUTO_CHECKED
SEED_REV = uid(f"{SEED}:lrev")
PUB = uid("dan-so-vung:published")  # seeded ACTIVE published version of gv.dia, grade 10
DUE = "2099-01-02T00:00:00+00:00"
OPEN = "2099-01-01T00:00:00+00:00"


def B(k: str, lesson: str = SEED) -> uuid.UUID:
    return uid(f"{lesson}:blk:{k}")


async def review(c: httpx.AsyncClient, block_id: object, h: str, action: str = "APPROVE", note: str | None = None) -> httpx.Response:
    return await c.post(f"/v1/blocks/{block_id}/reviews", json={"action": action, "contentHash": h, "note": note})


async def approve_all(c: httpx.AsyncClient, rev: str) -> None:
    for b in await blocks(c, rev):
        r = await review(c, b["id"], b["contentHash"])
        assert r.status_code == 201, (b["kind"], r.text)


async def lesson_version(c: httpx.AsyncClient, lesson: str) -> int:
    return int((await c.get(f"/v1/lessons/{lesson}")).json()["currentRevision"]["version"])


async def count(db: AsyncSession, table: str) -> int:
    return int(await db.scalar(text(f"SELECT count(*) FROM {table}")) or 0)  # noqa: S608 (test-only constant)


# ----------------------------------------------------------------------------- review + AT-14
async def test_queue_is_ordered_flagged_then_review_again_then_unreviewed(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    items = (await client.get(f"/v1/revisions/{uid('dien-tich-rung:lrev')}/review-queue")).json()["items"]
    assert [i["reviewStatus"] for i in items] == ["FLAGGED", "REVIEW_AGAIN", "UNREVIEWED"]
    only = (await client.get(f"/v1/revisions/{uid('dien-tich-rung:lrev')}/review-queue", params={"status": "REJECTED"})).json()
    assert [i["reviewStatus"] for i in only["items"]] == ["REJECTED"]


async def test_approval_is_bound_to_content_hash_and_sources(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    blk = next(b for b in await blocks(client, str(SEED_REV)) if b["id"] == str(B("p2")))
    r = await review(client, blk["id"], blk["contentHash"], note="Đã đối chiếu")
    assert r.status_code == 201 and r.json()["block"]["reviewStatus"] == "APPROVED"
    ev = (await db.execute(text("SELECT content_hash, source_hashes, reviewer_id, note FROM review_event WHERE block_id=:b"),
                           {"b": B("p2")})).one()
    assert ev[0] == blk["contentHash"] and len(ev[1]) >= 2 and str(ev[2]) == str(uid("user:gv.dia")) and ev[3] == "Đã đối chiếu"
    prov = (await client.get(f"/v1/blocks/{blk['id']}/provenance")).json()
    assert [x["isValid"] for x in prov["reviews"]] == [True]
    edit = await client.patch(f"/v1/blocks/{blk['id']}", json={"payload": {"text": "Đã sửa sau khi duyệt."}, "version": blk["version"]})
    assert edit.json()["reviewStatus"] == "REVIEW_AGAIN"
    assert [x["isValid"] for x in (await client.get(f"/v1/blocks/{blk['id']}/provenance")).json()["reviews"]] == [False]


async def test_at14_review_with_a_stale_hash_is_rejected_and_writes_nothing(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    blk = next(b for b in await blocks(client, str(SEED_REV)) if b["id"] == str(B("p2")))
    await client.patch(f"/v1/blocks/{blk['id']}", json={"payload": {"text": "Nội dung mới."}, "version": blk["version"]})
    before = await count(db, "review_event")
    r = await review(client, blk["id"], blk["contentHash"])  # the hash the reviewer saw is now old
    assert r.status_code == 409 and r.json()["code"] == "STALE_REVIEW"
    assert await count(db, "review_event") == before
    assert (await review(client, blk["id"], "0" * 64, "REJECT")).json()["code"] == "STALE_REVIEW"  # every action is bound


async def test_flagged_block_cannot_be_approved_but_can_be_rejected_or_sent_back(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "mock_inject", "new_number")
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    await generate(client, lesson)
    bad = next(b for b in await blocks(client, rev) if b["reviewStatus"] == "FLAGGED")
    blocked = await review(client, bad["id"], bad["contentHash"])
    assert blocked.status_code == 409 and blocked.json()["code"] == "APPROVE_BLOCKED"
    sent = await review(client, bad["id"], bad["contentHash"], "REQUEST_CHANGES", "Số liệu không có trong nguồn")
    assert sent.status_code == 201 and sent.json()["block"]["reviewStatus"] == "REVIEW_AGAIN"
    rej = await review(client, bad["id"], bad["contentHash"], "REJECT")
    assert rej.json()["block"]["reviewStatus"] == "REJECTED"


async def test_review_roles_and_idor(client: httpx.AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    blk = next(b for b in (await _blocks_as(client, "gv.dia@preclass.local")) if b["id"] == str(B("p2")))
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert (await review(client, blk["id"], blk["contentHash"])).status_code == 404  # not your lesson
    client.cookies.clear()
    await login(client, "HS10-01")
    assert (await review(client, blk["id"], blk["contentHash"])).status_code == 403
    client.cookies.clear()
    await login(client, "reviewer@preclass.local")
    assert (await review(client, blk["id"], blk["contentHash"])).json()["code"] == "FORBIDDEN_ROLE"  # flag off by default
    monkeypatch.setattr(get_settings(), "reviewer_enabled", True)
    assert (await review(client, blk["id"], blk["contentHash"])).status_code == 404  # not assigned
    await db.execute(text("INSERT INTO lesson_reviewer(lesson_id, reviewer_id) VALUES (:l, :r)"),
                     {"l": uid(f"{SEED}:lesson"), "r": uid("user:reviewer")})
    ok = await review(client, blk["id"], blk["contentHash"])
    assert ok.status_code == 201
    assert str(await db.scalar(text("SELECT reviewer_id FROM review_event WHERE block_id=:b"), {"b": B("p2")})) == str(uid("user:reviewer"))
    client.cookies.clear()
    assert (await review(client, blk["id"], blk["contentHash"])).status_code == 401


async def _blocks_as(c: httpx.AsyncClient, who: str) -> list[dict]:  # type: ignore[type-arg]
    await login(c, who)
    return await blocks(c, str(SEED_REV))


def test_the_only_bulk_approve_is_approve_all_for_clean_blocks() -> None:
    from app.main import app

    paths = [p for p in app.openapi()["paths"] if "approve" in p.lower() or "all" in p.rsplit("/", 1)[-1].lower()]
    assert paths == ["/v1/revisions/{revision_id}/approve-all"]  # PR-02 relaxed (K3): bulk only for blocks without warnings, nothing else


# ----------------------------------------------------------------------------- AT-10: the gate
async def test_at10_publish_is_blocked_while_blocks_are_unapproved_and_creates_no_snapshot(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    await generate(client, lesson)
    version = await lesson_version(client, lesson)
    check = (await client.get(f"/v1/revisions/{rev}/publish-check")).json()
    assert check["canPublish"] is False
    codes = {i["code"]: i for i in check["items"]}
    assert codes["ALL_APPROVED"]["ok"] is False and codes["NO_BLOCKERS"]["ok"] is True and codes["HAS_ITEMS"]["ok"] is True
    before = await count(db, "published_version")
    r = await client.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": True, "version": version})
    assert r.status_code == 409 and r.json()["code"] == "PUBLISH_BLOCKED"
    assert set(r.json()["blockIds"]) == {b["id"] for b in await blocks(client, rev)}
    assert await count(db, "published_version") == before  # no snapshot
    assert (await client.get(f"/v1/lessons/{lesson}")).json()["currentRevision"]["state"] == "DRAFT"


async def test_at10_a_blocker_stops_the_publish_even_when_everything_else_is_approved(
    client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "mock_inject", "new_number")
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    await generate(client, lesson)
    for b in await blocks(client, rev):
        if b["reviewStatus"] != "FLAGGED":
            assert (await review(client, b["id"], b["contentHash"])).status_code == 201
    check = {i["code"]: i for i in (await client.get(f"/v1/revisions/{rev}/publish-check")).json()["items"]}
    assert check["NO_BLOCKERS"]["ok"] is False and len(check["NO_BLOCKERS"]["blockIds"]) == 1
    r = await client.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": True, "version": await lesson_version(client, lesson)})
    assert r.status_code == 409 and r.json()["code"] == "PUBLISH_BLOCKED" and len(r.json()["blockIds"]) == 1


async def test_publish_needs_confirmation_and_the_current_version(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    await generate(client, lesson)
    await approve_all(client, rev)
    v = await lesson_version(client, lesson)
    no = await client.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": False, "version": v})
    assert no.status_code == 422 and no.json()["code"] == "CONFIRM_REQUIRED"
    stale = await client.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": True, "version": v + 3})
    assert stale.status_code == 409 and stale.json()["code"] == "VERSION_CONFLICT"


async def test_publish_freezes_the_revision_and_stores_an_immutable_snapshot(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)
    await generate(client, lesson)
    await approve_all(client, rev)
    assert (await client.get(f"/v1/revisions/{rev}/publish-check")).json()["canPublish"] is True
    v = await lesson_version(client, lesson)
    r = await client.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": True, "version": v})
    assert r.status_code == 201, r.text
    pub = r.json()
    assert pub["state"] == "ACTIVE" and pub["lessonTitle"] == "Bài thử" and pub["lessonRevisionId"] == rev
    row = (await db.execute(text("SELECT snapshot, snapshot_hash FROM published_version WHERE id=:i"), {"i": pub["id"]})).one()
    assert row[1] == pub["snapshotHash"] == sha256_hex(canonical_json(row[0]))
    assert len(row[0]["blocks"]) == len(await blocks(client, rev)) and row[0]["title"] == "Bài thử"
    cur = (await client.get(f"/v1/lessons/{lesson}")).json()
    assert cur["currentRevision"]["state"] == "PUBLISHED" and cur["currentRevision"]["version"] == v + 1
    assert cur["publishedVersionId"] == pub["id"]
    any_block = (await blocks(client, rev))[0]
    locked = [
        await client.patch(f"/v1/blocks/{any_block['id']}", json={"payload": {"text": "x"}, "version": any_block["version"]}),
        await review(client, any_block["id"], any_block["contentHash"], "REJECT"),
        await client.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": True, "version": v + 1}),
    ]
    assert [x.json()["code"] for x in locked] == ["REVISION_LOCKED"] * 3
    with pytest.raises(Exception, match="SNAPSHOT_IMMUTABLE"):  # the DB itself refuses
        await db.execute(text("UPDATE published_version SET snapshot='{}'::jsonb WHERE id=:i"), {"i": pub["id"]})


# ----------------------------------------------------------------------------- AT-11: edit after publish
async def test_at11_editing_after_publish_creates_a_new_revision_and_leaves_the_snapshot_alone(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    await login(client, "gv.dia@preclass.local")
    lesson, rev1 = await new_lesson(client)
    await generate(client, lesson)
    await approve_all(client, rev1)
    pub = (await client.post(f"/v1/revisions/{rev1}/publish", json={"confirmChecked": True, "version": await lesson_version(client, lesson)})).json()
    old_blocks = await blocks(client, rev1)

    new = await client.post(f"/v1/revisions/{rev1}/new-revision")
    assert new.status_code == 201, new.text
    rev2 = new.json()
    assert rev2["revisionNo"] == 2 and rev2["state"] == "DRAFT" and rev2["counts"]["approved"] == 0  # approvals do not carry over
    assert rev2["counts"]["total"] == len(old_blocks) and rev2["sourceRevisionIds"]
    items2 = await blocks(client, rev2["id"])
    assert {b["reviewStatus"] for b in items2} == {"AUTO_CHECKED"}
    assert sum(b["linkCount"] for b in items2) == sum(b["linkCount"] for b in old_blocks)  # provenance copied
    assert await db.scalar(text("SELECT count(*) FROM block_dependency d JOIN content_block b ON b.id=d.block_id WHERE b.revision_id=:r"),
                           {"r": uuid.UUID(rev2["id"])}) > 0

    target = next(b for b in items2 if b["kind"] == "paragraph")
    assert (await client.patch(f"/v1/blocks/{target['id']}", json={"payload": {"text": "Bản mới."}, "version": target["version"]})).status_code == 200
    assert (await db.scalar(text("SELECT snapshot_hash FROM published_version WHERE id=:i"), {"i": uuid.UUID(pub["id"])})) == pub["snapshotHash"]
    assert await blocks(client, rev1) == old_blocks  # the published revision is untouched
    assert (await client.get(f"/v1/lessons/{lesson}")).json()["currentRevision"]["id"] == rev2["id"]

    again = await client.post(f"/v1/revisions/{rev1}/new-revision")
    assert again.status_code == 409 and again.json()["code"] == "DRAFT_EXISTS"
    assert (await client.post(f"/v1/revisions/{rev2['id']}/new-revision")).json()["code"] == "NOT_PUBLISHED"

    await approve_all(client, rev2["id"])
    pub2 = await client.post(f"/v1/revisions/{rev2['id']}/publish", json={"confirmChecked": True, "version": rev2["version"]})
    assert pub2.status_code == 201
    states = dict((await db.execute(text("SELECT revision_no, state FROM lesson_revision WHERE lesson_id=:l"),
                                    {"l": uuid.UUID(lesson)})).all())
    assert states == {1: "SUPERSEDED", 2: "PUBLISHED"}
    assert await db.scalar(text("SELECT state FROM published_version WHERE id=:i"), {"i": uuid.UUID(pub["id"])}) == "ACTIVE"
    hist = (await client.get(f"/v1/lessons/{lesson}/history")).json()
    assert [r["state"] for r in hist["revisions"]] == ["SUPERSEDED", "PUBLISHED"]
    assert [e["operation"] for e in hist["events"]].count("PUBLISH") == 2


async def test_new_revision_guards(client: httpx.AsyncClient) -> None:
    await login(client, "gv.khac@preclass.local")
    assert (await client.post(f"/v1/revisions/{uid('dan-so-vung:lrev')}/new-revision")).status_code == 404  # not the author
    client.cookies.clear()
    await login(client, "gv.dia@preclass.local")
    assert (await client.post(f"/v1/revisions/{SEED_REV}/new-revision")).json()["code"] == "NOT_PUBLISHED"


# ----------------------------------------------------------------------------- AT-12 (teacher side) + assignments
async def test_at12_withdraw_records_the_reason_and_is_final(client: httpx.AsyncClient, db: AsyncSession) -> None:
    await login(client, "gv.dia@preclass.local")
    short = await client.post(f"/v1/published/{PUB}/withdraw", json={"reason": "x"})
    assert short.status_code == 422
    r = await client.post(f"/v1/published/{PUB}/withdraw", json={"reason": "Phát hiện sai số liệu ở câu 2."})
    assert r.status_code == 200 and r.json()["state"] == "WITHDRAWN" and r.json()["withdrawReason"].startswith("Phát hiện")
    assert await db.scalar(text("SELECT count(*) FROM audit_log WHERE action='WITHDRAW' AND resource_id=:i"), {"i": PUB}) == 1
    assert await db.scalar(text("SELECT count(*) FROM audit_log WHERE metadata <> '{}'::jsonb")) == 0  # reason is not copied into audit
    again = await client.post(f"/v1/published/{PUB}/withdraw", json={"reason": "Thử lại lần nữa"})
    assert again.status_code == 409 and again.json()["code"] == "ALREADY_WITHDRAWN"
    asg = await client.post(f"/v1/published/{PUB}/assignments", json={"classId": str(uid("class:10A1")), "openAt": OPEN, "dueAt": DUE})
    assert asg.status_code == 409 and asg.json()["code"] == "WITHDRAWN"
    hist = (await client.get(f"/v1/lessons/{uid('dan-so-vung:lesson')}/history")).json()["events"]
    assert {"PUBLISH", "WITHDRAW"} <= {e["operation"] for e in hist}


async def test_withdraw_is_author_only(client: httpx.AsyncClient) -> None:
    await login(client, "gv.khac@preclass.local")
    assert (await client.post(f"/v1/published/{PUB}/withdraw", json={"reason": "Không phải của tôi"})).status_code == 404
    client.cookies.clear()
    await login(client, "HS10-01")
    assert (await client.post(f"/v1/published/{PUB}/withdraw", json={"reason": "Học sinh thử"})).status_code == 403


async def test_assignments_checks_and_listing(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    ok = await client.post(f"/v1/published/{PUB}/assignments", json={"classId": str(uid("class:10A1")), "openAt": OPEN, "dueAt": DUE})
    assert ok.status_code == 201 and ok.json()["classCode"] == "10A1" and ok.json()["lessonTitle"].startswith("Phân bố")
    lesson_id = str(uid("dan-so-vung:lesson"))
    assert ok.json()["lessonId"] == lesson_id and ok.json()["revisionNo"] >= 1  # teachers see which lesson and version
    wrong_grade = await client.post(f"/v1/published/{PUB}/assignments", json={"classId": str(uid("class:11A1")), "openAt": OPEN, "dueAt": DUE})
    assert wrong_grade.status_code == 422 and wrong_grade.json()["code"] == "GRADE_MISMATCH"
    window = await client.post(f"/v1/published/{PUB}/assignments", json={"classId": str(uid("class:10A1")), "openAt": DUE, "dueAt": OPEN})
    assert window.status_code == 422 and window.json()["code"] == "INVALID_WINDOW"
    unknown = await client.post(f"/v1/published/{PUB}/assignments", json={"classId": str(uuid.uuid4()), "openAt": OPEN, "dueAt": DUE})
    assert unknown.status_code == 404
    taught = await client.post(f"/v1/published/{PUB}/assignments", json={"classId": str(uid("class:10A1")), "openAt": OPEN, "teachDate": "2099-01-10"})
    assert taught.status_code == 201 and taught.json()["dueAt"].startswith("2099-01-09T16:59")  # day before, 23:59 UTC+7
    neither = await client.post(f"/v1/published/{PUB}/assignments", json={"classId": str(uid("class:10A1")), "openAt": OPEN})
    assert neither.status_code == 422 and neither.json()["code"] == "DUE_REQUIRED"
    listed = (await client.get(f"/v1/classes/{uid('class:10A1')}/assignments")).json()["items"]
    assert all(i["lessonId"] == lesson_id and i["revisionNo"] == ok.json()["revisionNo"] for i in listed if i["publishedVersionId"] == str(PUB))
    assert {a["id"] for a in listed} >= {ok.json()["id"], str(uid("dan-so-vung:assignment"))}
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")  # teaches no class and does not own the version
    assert (await client.get(f"/v1/classes/{uid('class:10A1')}/assignments")).status_code == 404
    assert (await client.post(f"/v1/published/{PUB}/assignments", json={"classId": str(uid("class:10A1")), "openAt": OPEN, "dueAt": DUE})).status_code == 404
    client.cookies.clear()
    await login(client, "HS10-01")
    assert (await client.get(f"/v1/classes/{uid('class:10A1')}/assignments")).status_code == 403
