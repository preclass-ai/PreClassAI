import asyncpg
import pytest

pytestmark = pytest.mark.db

PUB = "(SELECT id FROM lesson_revision WHERE state='PUBLISHED')"

DENIED = [
    ("review_update", "UPDATE review_event SET note='x'", "APPEND_ONLY"),
    ("review_delete", "DELETE FROM review_event", "APPEND_ONLY"),
    ("validation_update", "UPDATE validation_result SET outcome='PASS'", "APPEND_ONLY"),
    ("transformation_delete", "DELETE FROM transformation_event", "APPEND_ONLY"),
    ("anchor_update", "UPDATE source_anchor SET excerpt='x'", "IMMUTABLE_SOURCE"),
    ("anchor_delete", "DELETE FROM source_anchor", "IMMUTABLE_SOURCE"),
    ("source_revision_sha", "UPDATE source_revision SET sha256='x'", "IMMUTABLE_SOURCE"),
    ("source_revision_delete", "DELETE FROM source_revision", "IMMUTABLE_SOURCE"),
    ("published_block_update", f"UPDATE content_block SET payload='{{}}'::jsonb WHERE revision_id={PUB}",
     "REVISION_LOCKED"),
    ("published_block_insert",
     f"INSERT INTO content_block(revision_id,kind,position,payload,content_hash,transformation) "
     f"VALUES ({PUB},'paragraph',99,'{{}}','h','ORIGINAL')", "REVISION_LOCKED"),
    ("published_link_delete",
     f"DELETE FROM provenance_link WHERE block_id IN (SELECT id FROM content_block WHERE revision_id={PUB})",
     "REVISION_LOCKED"),
    ("published_lesson_source_delete", f"DELETE FROM lesson_source WHERE lesson_revision_id={PUB}",
     "REVISION_LOCKED"),
    ("snapshot_update", "UPDATE published_version SET snapshot='{}'::jsonb", "SNAPSHOT_IMMUTABLE"),
    ("snapshot_delete", "DELETE FROM published_version", "SNAPSHOT_IMMUTABLE"),
    ("unpublish", "UPDATE lesson_revision SET state='DRAFT' WHERE state='PUBLISHED'",
     "INVALID_STATE_TRANSITION"),
    ("approve_without_event",
     "UPDATE content_block SET review_status='APPROVED' WHERE id="
     "(SELECT id FROM content_block WHERE review_status='AUTO_CHECKED' LIMIT 1)", "APPROVAL_INVALID"),
    ("edit_keeps_approved",
     "UPDATE content_block SET content_hash='deadbeef' WHERE review_status='APPROVED' AND revision_id IN "
     "(SELECT id FROM lesson_revision WHERE state='DRAFT')", "APPROVAL_INVALID"),
    ("hard_delete_block",
     "DELETE FROM content_block WHERE revision_id IN (SELECT id FROM lesson_revision WHERE state='DRAFT')",
     "NO_HARD_DELETE"),
    ("foreign_anchor_link",
     "INSERT INTO provenance_link(block_id, anchor_id, relation) "
     "SELECT b.id, a.id, 'supports' FROM content_block b, source_anchor a "
     "WHERE b.revision_id = (SELECT lr.id FROM lesson_revision lr JOIN lesson l ON l.id=lr.lesson_id "
     "                        WHERE l.title LIKE 'Tài nguyên rừng%') "
     "AND a.source_revision_id = (SELECT sr.id FROM source_revision sr JOIN source_asset sa ON sa.id=sr.asset_id "
     "                             WHERE sa.title LIKE 'Sản xuất lúa%') LIMIT 1", "ANCHOR_NOT_IN_LESSON"),
]


@pytest.mark.parametrize(("sql", "prefix"), [c[1:] for c in DENIED], ids=[c[0] for c in DENIED])
async def test_denied(conn: asyncpg.Connection, sql: str, prefix: str) -> None:
    with pytest.raises(asyncpg.RaiseError, match=f"^{prefix}"):
        await conn.execute(sql)


async def test_allowed_source_status_update(conn: asyncpg.Connection) -> None:
    await conn.execute("UPDATE source_revision SET extract_status='OK', locked_at=now()")


async def test_withdraw_is_final(conn: asyncpg.Connection) -> None:
    await conn.execute("UPDATE published_version SET state='WITHDRAWN', withdraw_reason='test'")
    with pytest.raises(asyncpg.RaiseError, match="^INVALID_STATE_TRANSITION"):
        await conn.execute("UPDATE published_version SET state='ACTIVE'")


async def test_approval_is_bound_to_hash(conn: asyncpg.Connection) -> None:
    b = await conn.fetchrow(
        "SELECT id, content_hash FROM content_block WHERE review_status='AUTO_CHECKED' "
        "AND revision_id IN (SELECT id FROM lesson_revision WHERE state='DRAFT') LIMIT 1")
    rev = await conn.fetchval("SELECT id FROM app_user WHERE email='gv.dia@preclass.local'")
    await conn.execute(
        "INSERT INTO review_event(block_id, content_hash, reviewer_id, action) VALUES ($1,$2,$3,'APPROVE')",
        b["id"], b["content_hash"], rev)
    await conn.execute("UPDATE content_block SET review_status='APPROVED' WHERE id=$1", b["id"])
    with pytest.raises(asyncpg.RaiseError, match="^APPROVAL_INVALID"):  # edited, status not reset
        async with conn.transaction():
            await conn.execute("UPDATE content_block SET content_hash='changed' WHERE id=$1", b["id"])
    await conn.execute(
        "UPDATE content_block SET content_hash='changed', review_status='REVIEW_AGAIN' WHERE id=$1", b["id"])


async def test_latest_review_wins(conn: asyncpg.Connection) -> None:
    """A later REQUEST_CHANGES on the same hash makes APPROVED invalid."""
    b = await conn.fetchrow(
        "SELECT id, content_hash FROM content_block WHERE review_status='AUTO_CHECKED' "
        "AND revision_id IN (SELECT id FROM lesson_revision WHERE state='DRAFT') LIMIT 1")
    rev = await conn.fetchval("SELECT id FROM app_user WHERE email='gv.dia@preclass.local'")
    for action in ("APPROVE", "REQUEST_CHANGES"):
        await conn.execute(
            "INSERT INTO review_event(block_id, content_hash, reviewer_id, action) VALUES ($1,$2,$3,$4)",
            b["id"], b["content_hash"], rev, action)
    with pytest.raises(asyncpg.RaiseError, match="^APPROVAL_INVALID"):
        await conn.execute("UPDATE content_block SET review_status='APPROVED' WHERE id=$1", b["id"])


async def test_one_attempt_per_item(conn: asyncpg.Connection) -> None:
    ids = await conn.fetchrow(
        "SELECT a.id AS aid, (SELECT id FROM app_user WHERE login_code='HS10-01') AS sid, "
        "(SELECT id FROM content_block WHERE kind='worksheet_item' AND revision_id IN "
        " (SELECT id FROM lesson_revision WHERE state='PUBLISHED') LIMIT 1) AS iid FROM assignment a")
    sql = ("INSERT INTO student_attempt(assignment_id, student_id, item_block_id, answer, request_id) "
           "VALUES ($1,$2,$3,'{}', gen_random_uuid())")
    await conn.execute(sql, ids["aid"], ids["sid"], ids["iid"])
    with pytest.raises(asyncpg.UniqueViolationError):
        await conn.execute(sql, ids["aid"], ids["sid"], ids["iid"])


async def test_seed_shape_and_invariants(conn: asyncpg.Connection) -> None:
    assert await conn.fetchval("SELECT count(*) FROM lesson") == 6
    assert await conn.fetchval("SELECT count(*) FROM app_user WHERE role='STUDENT'") == 30
    assert await conn.fetchval("SELECT count(*) FROM class") == 2
    # every APPROVED block has a matching latest APPROVE event
    bad = await conn.fetchval(
        "SELECT count(*) FROM content_block b WHERE b.review_status='APPROVED' AND NOT EXISTS ("
        " SELECT 1 FROM (SELECT action, content_hash FROM review_event WHERE block_id=b.id "
        "  ORDER BY created_at DESC LIMIT 1) e WHERE e.action='APPROVE' AND e.content_hash=b.content_hash)")
    assert bad == 0
    # a published revision contains only APPROVED blocks
    assert await conn.fetchval(
        "SELECT count(*) FROM content_block WHERE review_status<>'APPROVED' AND revision_id IN "
        "(SELECT id FROM lesson_revision WHERE state='PUBLISHED')") == 0
    # the seeded draft covers the interesting states
    states = {r[0] for r in await conn.fetch("SELECT DISTINCT review_status FROM content_block")}
    assert {"APPROVED", "AUTO_CHECKED", "FLAGGED", "REVIEW_AGAIN", "REJECTED", "UNREVIEWED"} <= states
    # PR-08 prerequisite: no replacement characters from encoding trouble
    assert await conn.fetchval("SELECT count(*) FROM source_anchor WHERE excerpt LIKE '%' || chr(65533) || '%'") == 0
