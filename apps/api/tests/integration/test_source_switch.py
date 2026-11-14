"""AT-08: switching a draft to a new source revision (one transaction, hash-bound approvals)."""

import uuid

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.ids import uid
from app.lessons import revision_out
from tests.conftest import login

pytestmark = pytest.mark.db

LESSON = "dien-tich-rung"  # seeded DRAFT: APPROVED, REVIEW_AGAIN, FLAGGED, REJECTED, UNREVIEWED, AUTO_CHECKED
LREV, SRC, ASSET = uid(f"{LESSON}:lrev"), uid(f"{LESSON}:srcrev"), uid(f"{LESSON}:asset")


async def _make_v2(db: AsyncSession) -> uuid.UUID:
    """Source revision 2 = copy of v1 with ONE changed table cell (the first value, anchor seq 007)."""
    new = uuid.uuid4()
    await db.execute(
        text("INSERT INTO source_revision(id, asset_id, version, sha256, mime, extract_status) "
             "VALUES (:n, :a, 2, 'sha-v2', 'text/plain', 'OK')"),
        {"n": new, "a": ASSET},
    )
    await db.execute(
        text(
            "INSERT INTO source_anchor(id, source_revision_id, code, kind, locator, excerpt, excerpt_hash, numbers) "
            "SELECT gen_random_uuid(), :n, replace(code, :o8, :n8), kind, locator, "
            " CASE WHEN code LIKE '%\\_007' THEN '4.100,0' ELSE excerpt END, "
            " CASE WHEN code LIKE '%\\_007' THEN 'changed-hash' ELSE excerpt_hash END, numbers "
            "FROM source_anchor WHERE source_revision_id = :o"
        ),
        {"n": new, "o": SRC, "n8": str(new)[:8], "o8": str(SRC)[:8]},
    )
    return new


async def _put(c: httpx.AsyncClient, new: uuid.UUID, version: int, rev: uuid.UUID = LREV) -> httpx.Response:
    return await c.put(f"/v1/revisions/{rev}/sources", json={"sourceRevisionIds": [str(new)], "version": version})


async def _statuses(db: AsyncSession) -> dict[uuid.UUID, str]:
    rows = await db.execute(text("SELECT id, review_status FROM content_block WHERE revision_id=:r"), {"r": LREV})
    return {r[0]: r[1] for r in rows}


async def test_switch_marks_review_again_unresolves_links_and_logs_events(
    client: httpx.AsyncClient, db: AsyncSession
) -> None:
    new = await _make_v2(db)
    rev = await db.get(m.LessonRevision, LREV)
    assert rev is not None and (await revision_out(db, rev)).newer_source_available is True
    linked = set(await db.scalars(text(
        "SELECT DISTINCT block_id FROM provenance_link l JOIN content_block b ON b.id=l.block_id "
        "WHERE b.revision_id=:r").bindparams(r=LREV)))
    parents = set(await db.scalars(text(
        "SELECT DISTINCT parent_id FROM content_block WHERE id = ANY(:ids) AND parent_id IS NOT NULL")
        .bindparams(ids=list(linked))))
    before = await _statuses(db)
    assert "APPROVED" in before.values()
    version = rev.version

    await login(client, "gv.dia@preclass.local")
    r = await _put(client, new, version)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["revision"]["version"] == version + 1 and body["revision"]["newerSourceAvailable"] is False
    assert body["revision"]["sourceRevisionIds"] == [str(new)]

    after = await _statuses(db)
    for bid in linked | parents:  # linked blocks (dependents are linked too) and the parent item
        assert after[bid] == "REVIEW_AGAIN"
    untouched = set(before) - linked - parents
    assert untouched and all(after[b] == before[b] for b in untouched)  # e.g. unlinked instruction / options

    st = {r[0]: r[1] for r in await db.execute(text(
        "SELECT l.status, count(*) FROM provenance_link l JOIN content_block b ON b.id=l.block_id "
        "WHERE b.revision_id=:r GROUP BY l.status"), {"r": LREV})}
    assert st["UNRESOLVED"] == body["unresolvedLinks"] > 0 and st["VERIFIED"] == body["matchedLinks"] > 0
    unresolved = await db.scalars(text(  # the changed cell is the only anchor that could not be re-matched
        "SELECT DISTINCT a.code FROM provenance_link l JOIN source_anchor a ON a.id=l.anchor_id "
        "JOIN content_block b ON b.id=l.block_id WHERE b.revision_id=:r AND l.status='UNRESOLVED'").bindparams(r=LREV))
    assert [c[-4:] for c in unresolved] == ["_007"]
    assert await db.scalar(text(  # every VERIFIED link now points into the new source revision
        "SELECT count(*) FROM provenance_link l JOIN source_anchor a ON a.id=l.anchor_id "
        "JOIN content_block b ON b.id=l.block_id WHERE b.revision_id=:r AND l.status='VERIFIED' "
        "AND a.source_revision_id<>:n").bindparams(r=LREV, n=new)) == 0
    assert await db.scalar(text(
        "SELECT count(*) FROM transformation_event e JOIN content_block b ON b.id=e.block_id "
        "WHERE b.revision_id=:r AND e.operation='SOURCE_REPLACED'").bindparams(r=LREV)) == len(linked | parents)


async def test_no_approval_survives_source_switch(client: httpx.AsyncClient, db: AsyncSession) -> None:
    new = await _make_v2(db)
    rev = await db.get(m.LessonRevision, LREV)
    assert rev is not None
    await login(client, "gv.dia@preclass.local")
    assert (await _put(client, new, rev.version)).status_code == 200
    assert "APPROVED" not in (await _statuses(db)).values()


async def test_switch_guards(client: httpx.AsyncClient, db: AsyncSession) -> None:
    new = await _make_v2(db)
    rev = await db.get(m.LessonRevision, LREV)
    assert rev is not None
    version = rev.version
    await login(client, "gv.dia@preclass.local")
    stale = await _put(client, new, version + 5)
    assert stale.status_code == 409 and stale.json()["code"] == "VERSION_CONFLICT"
    foreign = await _put(client, uid("xuat-khau:srcrev"), version)  # another teacher's PRIVATE source
    assert foreign.status_code == 404
    locked = await _put(client, uid("dan-so-vung:srcrev"), 1, uid("dan-so-vung:lrev"))
    assert locked.status_code == 409 and locked.json()["code"] == "REVISION_LOCKED"
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert (await _put(client, new, version)).status_code == 404  # not the author: IDOR → 404
    client.cookies.clear()
    await login(client, "HS10-01")
    assert (await _put(client, new, version)).status_code == 403
    client.cookies.clear()
    assert (await _put(client, new, version)).status_code == 401
