"""Lesson revision services."""

from uuid import UUID

from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.db import models as m
from app.errors import ApiError
from app.schemas import BlockCounts, RevisionOut, RevisionSourcesResult, RevisionSourcesUpdate

_STATUS_FIELD = {
    "APPROVED": "approved", "FLAGGED": "flagged", "REVIEW_AGAIN": "review_again", "UNREVIEWED": "unreviewed",
    "AUTO_CHECKED": "auto_checked", "REJECTED": "rejected",
}


async def revision_out(db: AsyncSession, rev: m.LessonRevision) -> RevisionOut:
    counts = BlockCounts()
    rows = await db.execute(
        select(m.ContentBlock.review_status, func.count())
        .where(m.ContentBlock.revision_id == rev.id, m.ContentBlock.deleted_at.is_(None))
        .group_by(m.ContentBlock.review_status)
    )
    for status, n in rows:
        setattr(counts, _STATUS_FIELD[status], n)
        counts.total += n
    src_ids = list(await db.scalars(select(m.LessonSource.source_revision_id).where(
        m.LessonSource.lesson_revision_id == rev.id)))
    newer = m.SourceRevision.__table__.alias("newer")
    has_newer = await db.scalar(
        select(func.count())
        .select_from(m.SourceRevision)
        .join(newer, (newer.c.asset_id == m.SourceRevision.asset_id) & (newer.c.version > m.SourceRevision.version))
        .where(m.SourceRevision.id.in_(src_ids))
    )
    return RevisionOut(
        id=rev.id, lesson_id=rev.lesson_id, revision_no=rev.revision_no, state=rev.state,
        version=rev.version, source_revision_ids=src_ids, newer_source_available=bool(has_newer), counts=counts,
        created_at=rev.created_at,
    )


async def replace_sources(
    db: AsyncSession, user: CurrentUser, revision_id: UUID, body: RevisionSourcesUpdate
) -> RevisionSourcesResult:
    """Switch a DRAFT revision to other source revisions in ONE transaction (AT-08, D-001 #7).

    Every block with a link to an anchor of a removed source revision, the blocks depending on it
    (transitively) and its direct parents go to REVIEW_AGAIN with a SOURCE_REPLACED event. Links whose
    anchor has an identical excerpt_hash in the new revision are re-pointed (VERIFIED); the rest become
    UNRESOLVED. Approval is bound to source hashes, so even re-matched blocks need a new review.
    """
    rev = await db.scalar(
        select(m.LessonRevision)
        .join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id)
        .where(m.LessonRevision.id == revision_id, m.Lesson.author_id == user.id)
        .with_for_update(of=m.LessonRevision)
    )
    if rev is None:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy")
    if rev.state != "DRAFT":
        raise ApiError(409, "REVISION_LOCKED", "Bản này không còn sửa được")
    if rev.version != body.version:
        raise ApiError(409, "VERSION_CONFLICT", "Bản đã thay đổi, hãy tải lại")

    new_ids = set(body.source_revision_ids)
    visible = set(await db.scalars(
        select(m.SourceRevision.id)
        .join(m.SourceAsset, m.SourceAsset.id == m.SourceRevision.asset_id)
        .where(m.SourceRevision.id.in_(new_ids),
               or_(m.SourceAsset.owner_id == user.id, m.SourceAsset.visibility == "SCHOOL"))
    ))
    if visible != new_ids:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy nguồn")
    old_ids = set(await db.scalars(select(m.LessonSource.source_revision_id).where(
        m.LessonSource.lesson_revision_id == rev.id)))
    removed, added = old_ids - new_ids, new_ids - old_ids
    if not removed and not added:
        return RevisionSourcesResult(revision=await revision_out(db, rev), matched_links=0, unresolved_links=0)

    if added:  # first, so re-pointed VERIFIED links satisfy the DB guard (anchor must be in lesson_source)
        await db.execute(insert(m.LessonSource),
                         [{"lesson_revision_id": rev.id, "source_revision_id": s} for s in added])

    # new anchors by (asset, excerpt_hash)
    new_by_key: dict[tuple[UUID, str], UUID] = {}
    for aid, asset, h in (await db.execute(
        select(m.SourceAnchor.id, m.SourceRevision.asset_id, m.SourceAnchor.excerpt_hash)
        .join(m.SourceRevision, m.SourceRevision.id == m.SourceAnchor.source_revision_id)
        .where(m.SourceAnchor.source_revision_id.in_(added or {UUID(int=0)}))
        .order_by(m.SourceAnchor.code)
    )):
        new_by_key.setdefault((asset, h), aid)

    old_links = (await db.execute(
        select(m.ProvenanceLink.id, m.ProvenanceLink.block_id, m.ProvenanceLink.anchor_id,
               m.SourceRevision.asset_id, m.SourceAnchor.excerpt_hash)
        .join(m.SourceAnchor, m.SourceAnchor.id == m.ProvenanceLink.anchor_id)
        .join(m.SourceRevision, m.SourceRevision.id == m.SourceAnchor.source_revision_id)
        .join(m.ContentBlock, m.ContentBlock.id == m.ProvenanceLink.block_id)
        .where(m.ContentBlock.revision_id == rev.id, m.ContentBlock.deleted_at.is_(None),
               m.SourceAnchor.source_revision_id.in_(removed or {UUID(int=0)}))
    )).all()
    taken: set[tuple[UUID, UUID]] = {
        (r[0], r[1]) for r in await db.execute(select(m.ProvenanceLink.block_id, m.ProvenanceLink.anchor_id))
    }
    matched = unresolved = 0
    for link_id, block_id, _anchor, asset, h in old_links:
        target = new_by_key.get((asset, h))
        if target is not None and (block_id, target) not in taken:
            await db.execute(update(m.ProvenanceLink).where(m.ProvenanceLink.id == link_id).values(
                anchor_id=target, status="VERIFIED"))
            taken.add((block_id, target))
            matched += 1
        else:
            await db.execute(update(m.ProvenanceLink).where(m.ProvenanceLink.id == link_id).values(
                status="UNRESOLVED"))
            unresolved += 1

    affected = {b for _, b, *_ in old_links}
    frontier = set(affected)
    while frontier:  # blocks depending (transitively) on an affected block
        nxt = set(await db.scalars(select(m.BlockDependency.block_id).where(
            m.BlockDependency.depends_on_block_id.in_(frontier))))
        frontier = nxt - affected
        affected |= nxt
    if affected:
        affected |= {p for p in await db.scalars(select(m.ContentBlock.parent_id).where(
            m.ContentBlock.id.in_(affected), m.ContentBlock.parent_id.is_not(None))) if p is not None}
        blocks = (await db.execute(select(m.ContentBlock.id, m.ContentBlock.content_hash).where(
            m.ContentBlock.id.in_(affected), m.ContentBlock.revision_id == rev.id,
            m.ContentBlock.deleted_at.is_(None)))).all()
        ids = [b for b, _ in blocks]
        await db.execute(update(m.ContentBlock).where(m.ContentBlock.id.in_(ids)).values(
            review_status="REVIEW_AGAIN", version=m.ContentBlock.version + 1))
        await db.execute(insert(m.TransformationEvent), [
            {"block_id": b, "actor_type": "TEACHER", "actor_id": user.id, "operation": "SOURCE_REPLACED",
             "before_hash": h, "after_hash": h} for b, h in blocks])
    if removed:
        await db.execute(delete(m.LessonSource).where(
            m.LessonSource.lesson_revision_id == rev.id, m.LessonSource.source_revision_id.in_(removed)))
    rev.version += 1
    await db.flush()
    await db.commit()
    await db.refresh(rev)
    return RevisionSourcesResult(revision=await revision_out(db, rev), matched_links=matched,
                                 unresolved_links=unresolved)
