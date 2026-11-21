"""Review, publish gate, snapshot, withdraw, new revision and assignments (GĐ8).

Every mutating operation locks the lesson_revision row FIRST (same order as block edits), so a publish and a concurrent
edit/review are serialised: whichever wins, the other sees the committed state and fails cleanly.
"""

import uuid
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit
from app.auth import CurrentUser
from app.blocks import NOT_FOUND, _readable, blocks_out, current_source_hashes, revision_for
from app.config import get_settings
from app.db import models as m
from app.errors import ApiError
from app.hashing import content_hash
from app.lessons import revision_out
from app.schemas import (
    AssignmentCreate,
    AssignmentList,
    AssignmentOut,
    PublishCheckItem,
    PublishCheckOut,
    PublishedOut,
    ReviewOut,
    ReviewQueue,
    ReviewRequest,
    RevisionOut,
)
from app.snapshot import build_snapshot
from app.validation import R, evaluate_revision, validate_revision

_LOCKED = ("PUBLISHED", "SUPERSEDED")
_PRIORITY = {"FLAGGED": 0, "REVIEW_AGAIN": 1, "UNREVIEWED": 2}
_NEW_STATUS = {"APPROVE": "APPROVED", "REJECT": "REJECTED", "REQUEST_CHANGES": "REVIEW_AGAIN"}


# ----------------------------------------------------------------------------- review
async def review_queue(db: AsyncSession, user: CurrentUser, revision_id: UUID, statuses: list[str]) -> ReviewQueue:
    await revision_for(db, user, revision_id, write=False)
    rows = (await db.scalars(select(m.ContentBlock).where(
        m.ContentBlock.revision_id == revision_id, m.ContentBlock.deleted_at.is_(None),
        m.ContentBlock.review_status.in_(statuses)))).all()
    rows = sorted(rows, key=lambda b: (_PRIORITY.get(b.review_status, 9), b.position))
    return ReviewQueue(items=await blocks_out(db, list(rows)))


async def review_block(db: AsyncSession, user: CurrentUser, block_id: UUID, body: ReviewRequest) -> ReviewOut:
    if user.role == "REVIEWER" and not get_settings().reviewer_enabled:  # second reviewer is a config flag, off by default
        raise ApiError(403, "FORBIDDEN_ROLE", "Bạn không có quyền thực hiện thao tác này")
    rev_id = await db.scalar(select(m.ContentBlock.revision_id).where(
        m.ContentBlock.id == block_id, m.ContentBlock.deleted_at.is_(None)))
    if rev_id is None:
        raise NOT_FOUND
    rev = await db.scalar(
        select(m.LessonRevision).join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id)
        .where(m.LessonRevision.id == rev_id, _readable(user)).with_for_update(of=m.LessonRevision))
    if rev is None:
        raise NOT_FOUND
    if rev.state in _LOCKED:
        raise ApiError(409, "REVISION_LOCKED", "Bản này không còn sửa được")
    block = await db.scalar(select(m.ContentBlock).where(
        m.ContentBlock.id == block_id, m.ContentBlock.deleted_at.is_(None)).with_for_update())
    if block is None:
        raise NOT_FOUND
    if body.content_hash != block.content_hash:  # AT-14: approval is bound to the hash the reviewer saw
        raise ApiError(409, "STALE_REVIEW", "Nội dung đã thay đổi sau khi bạn xem")
    shashes: list[str] = []
    if body.action == "APPROVE":
        _, evaluated = await evaluate_revision(db, rev.id)
        if any(r.outcome == "FAIL" and r.severity == "BLOCKER" and r.rule != "VAL-06" for r in evaluated[block.id]):
            raise ApiError(409, "APPROVE_BLOCKED", "Khối còn lỗi chặn, hãy sửa trước khi duyệt")
        shashes = await current_source_hashes(db, block.id)
    event_id = uuid.uuid4()
    await db.execute(insert(m.ReviewEvent), [{
        "id": event_id, "block_id": block.id, "content_hash": block.content_hash, "source_hashes": shashes,
        "reviewer_id": user.id, "action": body.action, "note": body.note}])
    await db.execute(update(m.ContentBlock).where(m.ContentBlock.id == block.id).values(
        review_status=_NEW_STATUS[body.action]))  # APPROVED is re-checked by the DB trigger
    await db.commit()
    await db.refresh(block)
    return ReviewOut(block=(await blocks_out(db, [block]))[0], review_event_id=event_id)


# ----------------------------------------------------------------------------- publish gate
def _gate(blocks: list[m.ContentBlock], evaluated: dict[UUID, list[R]]) -> list[PublishCheckItem]:
    def fails(b: m.ContentBlock, severity: str | None = None, rule: str | None = None) -> bool:
        return any(r.outcome == "FAIL" and (severity is None or r.severity == severity) and (rule is None or r.rule == rule)
                   for r in evaluated[b.id])

    not_approved = [b.id for b in blocks if b.review_status != "APPROVED" or fails(b, rule="VAL-06")]
    blockers = [b.id for b in blocks if fails(b, "BLOCKER")]
    bad_sources = [b.id for b in blocks if fails(b, rule="VAL-01")]
    has_items = any(b.kind in ("worksheet_item", "card_front") for b in blocks)
    return [
        PublishCheckItem(code="ALL_APPROVED", ok=not not_approved, block_ids=not_approved,
                         message="Mọi khối đã được duyệt." if not not_approved
                         else f"Còn {len(not_approved)} khối chưa được duyệt hoặc duyệt không còn hiệu lực."),
        PublishCheckItem(code="NO_BLOCKERS", ok=not blockers, block_ids=blockers,
                         message="Không còn cảnh báo chặn." if not blockers else f"Còn {len(blockers)} khối có lỗi chặn."),
        PublishCheckItem(code="SOURCES_VALID", ok=not bad_sources, block_ids=bad_sources,
                         message="Mọi nguồn đều hợp lệ." if not bad_sources else "Có khối liên kết nguồn không hợp lệ."),
        PublishCheckItem(code="HAS_ITEMS", ok=has_items,
                         message="Có câu hỏi/thẻ." if has_items else "Bản chưa có câu hỏi hoặc thẻ nào."),
    ]


async def publish_check(db: AsyncSession, user: CurrentUser, revision_id: UUID) -> PublishCheckOut:
    await revision_for(db, user, revision_id, write=False)
    blocks, evaluated = await evaluate_revision(db, revision_id)  # read-only, fresh
    items = _gate(blocks, evaluated)
    return PublishCheckOut(can_publish=all(i.ok for i in items), items=items)


def _out(pv: m.PublishedVersion, title: str) -> PublishedOut:
    return PublishedOut(id=pv.id, lesson_revision_id=pv.lesson_revision_id, lesson_title=title, state=pv.state,
                        snapshot_hash=pv.snapshot_hash, published_by=pv.published_by, published_at=pv.created_at,
                        withdraw_reason=pv.withdraw_reason)


async def publish(db: AsyncSession, user: CurrentUser, revision_id: UUID, confirm: bool, version: int) -> PublishedOut:
    rev = await revision_for(db, user, revision_id, write=True)  # locks the revision; 409 REVISION_LOCKED if published
    if not confirm:
        raise ApiError(422, "CONFIRM_REQUIRED", "Cần xác nhận đã kiểm tra nội dung")
    if rev.version != version:
        raise ApiError(409, "VERSION_CONFLICT", "Bản đã thay đổi, hãy tải lại")
    blocks, evaluated = await evaluate_revision(db, rev.id)
    items = _gate(blocks, evaluated)
    if not all(i.ok for i in items):  # AT-10: nothing is written
        ids = sorted({b for i in items for b in i.block_ids}, key=str)
        raise ApiError(409, "PUBLISH_BLOCKED", "Chưa đủ điều kiện xuất bản", extra={"blockIds": [str(b) for b in ids]})
    lesson = await db.get(m.Lesson, rev.lesson_id)
    if lesson is None:
        raise NOT_FOUND
    snapshot, snap_hash = build_snapshot(lesson.title, lesson.grade, [
        {"id": b.id, "kind": b.kind, "parent_id": b.parent_id, "position": b.position, "payload": b.payload}
        for b in blocks])
    pv = m.PublishedVersion(lesson_revision_id=rev.id, snapshot=snapshot, snapshot_hash=snap_hash, published_by=user.id)
    db.add(pv)
    await db.flush()
    await db.execute(update(m.LessonRevision).where(
        m.LessonRevision.lesson_id == rev.lesson_id, m.LessonRevision.id != rev.id,
        m.LessonRevision.state == "PUBLISHED").values(state="SUPERSEDED"))
    rev.state, rev.version = "PUBLISHED", rev.version + 1  # blocks are frozen from here (trigger)
    audit(db, user.id, "PUBLISH", "published_version", pv.id)
    await db.commit()
    await db.refresh(pv)
    return _out(pv, lesson.title)


# ----------------------------------------------------------------------------- new revision (AT-11)
async def new_revision(db: AsyncSession, user: CurrentUser, revision_id: UUID) -> RevisionOut:
    src = await db.scalar(
        select(m.LessonRevision).join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id)
        .where(m.LessonRevision.id == revision_id, m.Lesson.author_id == user.id).with_for_update(of=m.LessonRevision))
    if src is None:
        raise NOT_FOUND
    if src.state != "PUBLISHED":
        raise ApiError(409, "NOT_PUBLISHED", "Chỉ tạo bản mới từ bản đã xuất bản")
    if await db.scalar(select(m.LessonRevision.id).where(
            m.LessonRevision.lesson_id == src.lesson_id, m.LessonRevision.state.in_(("DRAFT", "IN_REVIEW")))):
        raise ApiError(409, "DRAFT_EXISTS", "Đã có bản nháp đang soạn")
    top = await db.scalar(select(func.max(m.LessonRevision.revision_no)).where(m.LessonRevision.lesson_id == src.lesson_id))
    new = m.LessonRevision(lesson_id=src.lesson_id, revision_no=(top or 0) + 1, state="DRAFT", base_revision_id=src.id)
    db.add(new)
    await db.flush()
    srcs = list(await db.scalars(select(m.LessonSource.source_revision_id).where(m.LessonSource.lesson_revision_id == src.id)))
    if srcs:
        await db.execute(insert(m.LessonSource), [{"lesson_revision_id": new.id, "source_revision_id": s} for s in srcs])
    old = list((await db.scalars(select(m.ContentBlock).where(
        m.ContentBlock.revision_id == src.id, m.ContentBlock.deleted_at.is_(None)))).all())
    mapping = {b.id: uuid.uuid4() for b in old}
    by_id = {b.id: b for b in old}

    def depth(b: m.ContentBlock) -> int:
        return 0 if b.parent_id not in by_id else 1 + depth(by_id[b.parent_id])

    rows, events = [], []
    for b in sorted(old, key=lambda x: (depth(x), x.position)):  # parents first (FK)
        parent = mapping.get(b.parent_id) if b.parent_id else None
        h = content_hash(b.kind, b.payload, str(parent) if parent else None, b.transformation, b.no_source_reason)
        rows.append({"id": mapping[b.id], "revision_id": new.id, "kind": b.kind, "parent_id": parent, "position": b.position,
                     "payload": b.payload, "content_hash": h, "transformation": b.transformation,
                     "no_source_reason": b.no_source_reason, "is_factual": b.is_factual,
                     "competency_code": b.competency_code, "objective_id": b.objective_id})  # approvals are NOT carried over
        events.append({"block_id": mapping[b.id], "actor_type": "SYSTEM", "operation": "EDIT", "before_hash": None,
                       "after_hash": h})
    if rows:
        await db.execute(insert(m.ContentBlock), rows)
        links = (await db.execute(select(m.ProvenanceLink).where(m.ProvenanceLink.block_id.in_(list(mapping))))).scalars().all()
        if links:
            await db.execute(insert(m.ProvenanceLink), [{
                "block_id": mapping[lk.block_id], "anchor_id": lk.anchor_id, "relation": lk.relation,
                "rationale": lk.rationale, "status": lk.status} for lk in links])
        deps = (await db.execute(select(m.BlockDependency).where(m.BlockDependency.block_id.in_(list(mapping))))).scalars().all()
        if deps:
            await db.execute(insert(m.BlockDependency), [{
                "block_id": mapping[d.block_id], "depends_on_block_id": mapping[d.depends_on_block_id], "kind": d.kind}
                for d in deps if d.depends_on_block_id in mapping])
        await db.execute(insert(m.TransformationEvent), events)
    await db.commit()
    await validate_revision(db, new.id)  # UNREVIEWED -> AUTO_CHECKED / FLAGGED
    await db.refresh(new)
    return await revision_out(db, new)


# ----------------------------------------------------------------------------- withdraw and assignments
async def _owned_version(
    db: AsyncSession, user: CurrentUser, published_id: UUID, *, lock: bool
) -> tuple[m.PublishedVersion, m.Lesson]:
    q = (select(m.PublishedVersion, m.Lesson)
         .join(m.LessonRevision, m.LessonRevision.id == m.PublishedVersion.lesson_revision_id)
         .join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id)
         .where(m.PublishedVersion.id == published_id, m.Lesson.author_id == user.id))
    row = (await db.execute(q.with_for_update(of=m.PublishedVersion) if lock else q)).first()
    if row is None:
        raise NOT_FOUND
    return row[0], row[1]


async def withdraw(db: AsyncSession, user: CurrentUser, published_id: UUID, reason: str) -> PublishedOut:
    pv, lesson = await _owned_version(db, user, published_id, lock=True)
    if pv.state == "WITHDRAWN":
        raise ApiError(409, "ALREADY_WITHDRAWN", "Bản này đã được thu hồi")
    pv.state, pv.withdraw_reason = "WITHDRAWN", reason.strip()  # the reason is stored with the version (logged)
    audit(db, user.id, "WITHDRAW", "published_version", pv.id)  # audit never carries free text
    await db.commit()
    await db.refresh(pv)
    return _out(pv, lesson.title)


def _assignment_out(a: m.Assignment, code: str, title: str) -> AssignmentOut:
    return AssignmentOut(id=a.id, published_version_id=a.published_version_id, class_id=a.class_id, class_code=code,
                         lesson_title=title, open_at=a.open_at, due_at=a.due_at)


async def create_assignment(
    db: AsyncSession, user: CurrentUser, published_id: UUID, body: AssignmentCreate
) -> AssignmentOut:
    pv, lesson = await _owned_version(db, user, published_id, lock=True)
    cls = await db.scalar(
        select(m.Class).join(m.ClassMember, m.ClassMember.class_id == m.Class.id)
        .where(m.Class.id == body.class_id, m.ClassMember.user_id == user.id, m.ClassMember.role_in_class == "TEACHER"))
    if cls is None:
        raise NOT_FOUND  # not your class
    if pv.state != "ACTIVE":
        raise ApiError(409, "WITHDRAWN", "Bản đã thu hồi, không thể giao bài")
    due = body.due_at
    if due is None and body.teach_date is not None:
        from app.lessonplan.service import due_before

        due = due_before(body.teach_date)
    if due is None:
        raise ApiError(422, "DUE_REQUIRED", "Cần hạn nộp hoặc ngày học")
    if due <= body.open_at:
        raise ApiError(422, "INVALID_WINDOW", "Hạn nộp phải sau thời điểm mở bài")
    if cls.grade != lesson.grade:
        raise ApiError(422, "GRADE_MISMATCH", "Khối lớp không khớp với bài giảng")
    a = m.Assignment(published_version_id=pv.id, class_id=cls.id, open_at=body.open_at, due_at=due)
    db.add(a)
    audit(db, user.id, "ASSIGN", "assignment", None)
    await db.commit()
    return _assignment_out(a, cls.code, lesson.title)


async def list_class_assignments(db: AsyncSession, user: CurrentUser, class_id: UUID) -> AssignmentList:
    cls = await db.scalar(
        select(m.Class).join(m.ClassMember, m.ClassMember.class_id == m.Class.id)
        .where(m.Class.id == class_id, m.ClassMember.user_id == user.id, m.ClassMember.role_in_class == "TEACHER"))
    if cls is None:
        raise NOT_FOUND
    rows = (await db.execute(
        select(m.Assignment, m.Lesson.title)
        .join(m.PublishedVersion, m.PublishedVersion.id == m.Assignment.published_version_id)
        .join(m.LessonRevision, m.LessonRevision.id == m.PublishedVersion.lesson_revision_id)
        .join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id)
        .where(m.Assignment.class_id == class_id).order_by(m.Assignment.open_at.desc()))).all()
    return AssignmentList(items=[_assignment_out(a, cls.code, t) for a, t in rows])


