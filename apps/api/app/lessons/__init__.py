"""Lesson revision services."""

from uuid import UUID

from sqlalchemy import delete, func, insert, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.blocks import _readable
from app.db import models as m
from app.errors import ApiError
from app.schemas import (
    BlockCounts,
    HistoryEvent,
    HistoryRevision,
    LessonCreate,
    LessonHistory,
    LessonList,
    LessonOut,
    RevisionOut,
    RevisionSourcesResult,
    RevisionSourcesUpdate,
)

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


async def _reject_failed(db: AsyncSession, ids: set[UUID]) -> None:
    """A source whose text could not be read (e.g. a scanned PDF) has no anchors: it cannot feed a lesson."""
    if ids and await db.scalar(select(m.SourceRevision.id).where(
            m.SourceRevision.id.in_(ids), m.SourceRevision.extract_status != "OK").limit(1)):
        raise ApiError(422, "SOURCE_NOT_READABLE", "Nguồn chưa đọc được nội dung chữ, hãy nạp bản có chữ")


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
    await _reject_failed(db, new_ids)
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


async def _lesson_out(db: AsyncSession, lesson: m.Lesson) -> LessonOut:
    rev = await db.scalar(select(m.LessonRevision).where(m.LessonRevision.lesson_id == lesson.id)
                          .order_by(m.LessonRevision.revision_no.desc()).limit(1))
    if rev is None:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy")
    pub = await db.scalar(
        select(m.PublishedVersion.id).join(m.LessonRevision, m.LessonRevision.id == m.PublishedVersion.lesson_revision_id)
        .where(m.LessonRevision.lesson_id == lesson.id, m.PublishedVersion.state == "ACTIVE")
        .order_by(m.PublishedVersion.created_at.desc()).limit(1))
    return LessonOut(id=lesson.id, title=lesson.title, grade=lesson.grade, goal=lesson.goal, author_id=lesson.author_id,
                     current_revision=await revision_out(db, rev), published_version_id=pub,
                     teach_date=lesson.teach_date, created_at=lesson.created_at)


async def _readable_lesson(db: AsyncSession, user: CurrentUser, lesson_id: UUID) -> m.Lesson:
    lesson = await db.scalar(select(m.Lesson).where(m.Lesson.id == lesson_id, _readable(user)))
    if lesson is None:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy")
    return lesson


async def create_lesson(db: AsyncSession, user: CurrentUser, body: LessonCreate) -> LessonOut:
    wanted = set(body.source_revision_ids)
    visible = set(await db.scalars(
        select(m.SourceRevision.id).join(m.SourceAsset, m.SourceAsset.id == m.SourceRevision.asset_id)
        .where(m.SourceRevision.id.in_(wanted), or_(m.SourceAsset.owner_id == user.id,
                                                    m.SourceAsset.visibility == "SCHOOL"))))
    if visible != wanted:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy nguồn")
    await _reject_failed(db, wanted)
    lesson = m.Lesson(author_id=user.id, grade=body.grade, title=body.title.strip(), goal=body.goal)
    db.add(lesson)
    await db.flush()
    rev = m.LessonRevision(lesson_id=lesson.id, revision_no=1, state="DRAFT")
    db.add(rev)
    await db.flush()
    await db.execute(insert(m.LessonSource), [{"lesson_revision_id": rev.id, "source_revision_id": s} for s in wanted])
    await db.commit()
    return await _lesson_out(db, lesson)


async def list_lessons(db: AsyncSession, user: CurrentUser) -> LessonList:
    lessons = (await db.scalars(select(m.Lesson).where(_readable(user)).order_by(
        m.Lesson.created_at.desc(), m.Lesson.title))).all()
    return LessonList(items=[await _lesson_out(db, x) for x in lessons])


async def get_lesson(db: AsyncSession, user: CurrentUser, lesson_id: UUID) -> LessonOut:
    return await _lesson_out(db, await _readable_lesson(db, user, lesson_id))


async def lesson_history(db: AsyncSession, user: CurrentUser, lesson_id: UUID) -> LessonHistory:
    await _readable_lesson(db, user, lesson_id)
    revs = (await db.execute(
        select(m.LessonRevision, func.count(m.ContentBlock.id).filter(m.ContentBlock.deleted_at.is_(None)),
               m.PublishedVersion.created_at)
        .outerjoin(m.ContentBlock, m.ContentBlock.revision_id == m.LessonRevision.id)
        .outerjoin(m.PublishedVersion, m.PublishedVersion.lesson_revision_id == m.LessonRevision.id)
        .where(m.LessonRevision.lesson_id == lesson_id)
        .group_by(m.LessonRevision.id, m.PublishedVersion.created_at).order_by(m.LessonRevision.revision_no))).all()
    t = (await db.execute(
        select(m.TransformationEvent, m.ContentBlock.revision_id)
        .join(m.ContentBlock, m.ContentBlock.id == m.TransformationEvent.block_id)
        .join(m.LessonRevision, m.LessonRevision.id == m.ContentBlock.revision_id)
        .where(m.LessonRevision.lesson_id == lesson_id).order_by(m.TransformationEvent.created_at.desc()).limit(200))).all()
    r = (await db.execute(
        select(m.ReviewEvent).join(m.ContentBlock, m.ContentBlock.id == m.ReviewEvent.block_id)
        .join(m.LessonRevision, m.LessonRevision.id == m.ContentBlock.revision_id)
        .where(m.LessonRevision.lesson_id == lesson_id).order_by(m.ReviewEvent.created_at.desc()).limit(200))).scalars().all()
    events = [HistoryEvent(at=e.created_at, actor_type=e.actor_type, actor_id=e.actor_id, operation=e.operation,
                           block_id=e.block_id) for e, _ in t]
    events += [HistoryEvent(at=x.created_at, actor_type="TEACHER", actor_id=x.reviewer_id, operation="REVIEW",
                            block_id=x.block_id, summary=x.action) for x in r]
    pubs = (await db.execute(select(m.PublishedVersion).join(
        m.LessonRevision, m.LessonRevision.id == m.PublishedVersion.lesson_revision_id)
        .where(m.LessonRevision.lesson_id == lesson_id))).scalars().all()
    events += [HistoryEvent(at=p.created_at, actor_type="TEACHER", actor_id=p.published_by, operation="PUBLISH") for p in pubs]
    if pubs:
        wd = (await db.execute(select(m.AuditLog).where(
            m.AuditLog.action == "WITHDRAW", m.AuditLog.resource_id.in_([p.id for p in pubs])))).scalars().all()
        events += [HistoryEvent(at=a.created_at, actor_type="TEACHER", actor_id=a.actor_id, operation="WITHDRAW") for a in wd]
    events.sort(key=lambda e: e.at, reverse=True)
    return LessonHistory(
        revisions=[HistoryRevision(revision_id=v.id, revision_no=v.revision_no, state=v.state, published_at=pub,
                                   block_count=n) for v, n, pub in revs],
        events=events[:200])
