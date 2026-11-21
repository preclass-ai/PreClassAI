"""Content blocks, provenance and invalidation (GĐ6).

Rules (D-001 #5/#6, Khải review 14/11):
- Only the lesson author edits; an assigned REVIEWER may read. Anything else is 404.
- Editing a block changes its content_hash. APPROVED -> REVIEW_AGAIN for the block, the blocks depending on it
  (transitively) and its direct parent. A stale AUTO_CHECKED/FLAGGED result becomes UNREVIEWED until validation reruns.
- PUBLISHED/SUPERSEDED revisions are frozen (409 REVISION_LOCKED); the DB triggers enforce it too.
"""

from typing import Any
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy import and_, delete, exists, false, func, insert, or_, select, true, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit
from app.auth import CurrentUser
from app.db import models as m
from app.errors import ApiError
from app.hashing import content_hash, source_hashes
from app.schemas import (
    AnchorRef,
    AnswerKeyPayload,
    ApiModel,
    BlockCreate,
    BlockList,
    BlockOut,
    CardPayload,
    DataFactPayload,
    ExplanationPayload,
    HeadingPayload,
    InstructionPayload,
    OptionPayload,
    ParagraphPayload,
    ProvenanceLinkOut,
    ProvenanceOut,
    ProvenanceUpdate,
    ReviewEventOut,
    TransformationEventOut,
    ValidationResultOut,
    WorksheetItemPayload,
)

NOT_FOUND = ApiError(404, "NOT_FOUND", "Không tìm thấy")
PAYLOAD: dict[str, type[ApiModel]] = {
    "heading": HeadingPayload, "paragraph": ParagraphPayload, "instruction": InstructionPayload,
    "data_fact": DataFactPayload, "worksheet_item": WorksheetItemPayload, "option": OptionPayload,
    "answer_key": AnswerKeyPayload, "explanation": ExplanationPayload, "card_front": CardPayload,
    "card_back": CardPayload,
}
_KEEP: Any = object()  # sentinel: leave noSourceReason unchanged
_DEP_KIND = {"option": "LABEL_OF", "answer_key": "ANSWER_OF", "card_back": "ANSWER_OF", "explanation": "EXPLANATION_OF"}


def normalize_payload(kind: str, raw: Any) -> dict[str, Any]:
    """Validate a payload against its kind (unknown keys rejected) and return the stored shape."""
    model = PAYLOAD.get(kind)
    if model is None or not isinstance(raw, dict):
        raise ApiError(422, "PAYLOAD_INVALID", "Nội dung khối không hợp lệ")
    raw = {k: v for k, v in raw.items() if v is not None}  # responses carry nulls for unused fields: tolerate a round trip
    allowed = {f.alias or n for n, f in model.model_fields.items()}
    if set(raw) - allowed:
        raise ApiError(422, "PAYLOAD_INVALID", "Nội dung khối có trường không hợp lệ")
    try:
        data = model.model_validate(raw).model_dump(by_alias=True, exclude_none=True, mode="json")
    except ValidationError as e:
        raise ApiError(422, "PAYLOAD_INVALID", "Nội dung khối không hợp lệ") from e
    if kind == "answer_key" and not (
        "correct" in data or ("value" in data and "unit" in data) or "rubricPoints" in data
    ):
        raise ApiError(422, "PAYLOAD_INVALID", "Đáp án cần correct, hoặc value + unit, hoặc rubricPoints")
    return data


# ----------------------------------------------------------------------------- access
def _readable(user: CurrentUser):  # type: ignore[no-untyped-def]
    reviewer = and_(
        true() if user.role == "REVIEWER" else false(),
        exists().where(m.LessonReviewer.lesson_id == m.Lesson.id, m.LessonReviewer.reviewer_id == user.id),
    )
    return or_(m.Lesson.author_id == user.id, reviewer)


async def revision_for(
    db: AsyncSession, user: CurrentUser, revision_id: UUID, *, write: bool
) -> m.LessonRevision:
    q = (select(m.LessonRevision).join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id)
         .where(m.LessonRevision.id == revision_id))
    q = q.where(m.Lesson.author_id == user.id).with_for_update(of=m.LessonRevision) if write else q.where(_readable(user))
    rev = await db.scalar(q)
    if rev is None:
        raise NOT_FOUND
    if write and rev.state in ("PUBLISHED", "SUPERSEDED"):
        raise ApiError(409, "REVISION_LOCKED", "Bản này không còn sửa được")
    return rev


async def block_for(db: AsyncSession, user: CurrentUser, block_id: UUID, *, write: bool) -> m.ContentBlock:
    rev_id = await db.scalar(select(m.ContentBlock.revision_id).where(
        m.ContentBlock.id == block_id, m.ContentBlock.deleted_at.is_(None)))
    if rev_id is None:
        raise NOT_FOUND
    await revision_for(db, user, rev_id, write=write)  # 404 / 409 before we lock the block
    q = select(m.ContentBlock).where(m.ContentBlock.id == block_id, m.ContentBlock.deleted_at.is_(None))
    block = await db.scalar(q.with_for_update() if write else q)
    if block is None:
        raise NOT_FOUND
    return block


# ----------------------------------------------------------------------------- output
async def blocks_out(db: AsyncSession, blocks: list[m.ContentBlock]) -> list[BlockOut]:
    ids = [b.id for b in blocks]
    links = dict((await db.execute(
        select(m.ProvenanceLink.block_id, func.count()).where(m.ProvenanceLink.block_id.in_(ids))
        .group_by(m.ProvenanceLink.block_id))).all()) if ids else {}
    rows = (await db.execute(  # newest first: the first row per (block, rule) is the latest result
        select(m.ValidationResult.block_id, m.ValidationResult.rule, m.ValidationResult.severity,
               m.ValidationResult.outcome, m.ValidationResult.content_hash)
        .where(m.ValidationResult.block_id.in_(ids)).order_by(m.ValidationResult.created_at.desc()))).all() if ids else []
    seen_rules: set[tuple[UUID, str]] = set()
    latest = []
    for bid, rule, sev, outcome, h in rows:
        if (bid, rule) not in seen_rules:
            seen_rules.add((bid, rule))
            latest.append((bid, sev, outcome, h))
    hashes = {b.id: b.content_hash for b in blocks}
    blocker: dict[UUID, int] = {}
    warning: dict[UUID, int] = {}
    for bid, sev, outcome, h in latest:
        if outcome == "FAIL" and h == hashes[bid]:
            bucket = blocker if sev == "BLOCKER" else warning
            bucket[bid] = bucket.get(bid, 0) + 1
    return [BlockOut(
        id=b.id, revision_id=b.revision_id, kind=b.kind, parent_id=b.parent_id, position=b.position,
        payload=b.payload, content_hash=b.content_hash, transformation=b.transformation,
        review_status=b.review_status, no_source_reason=b.no_source_reason, is_factual=b.is_factual,
        competency_code=b.competency_code, objective_id=b.objective_id,
        remediation_draft=b.remediation_draft, version=b.version,
        link_count=links.get(b.id, 0), blocker_count=blocker.get(b.id, 0),
        warning_count=warning.get(b.id, 0)) for b in blocks]


async def list_blocks(db: AsyncSession, user: CurrentUser, revision_id: UUID) -> BlockList:
    await revision_for(db, user, revision_id, write=False)
    rows = (await db.scalars(select(m.ContentBlock).where(
        m.ContentBlock.revision_id == revision_id, m.ContentBlock.deleted_at.is_(None))
        .order_by(m.ContentBlock.position))).all()
    return BlockList(items=await blocks_out(db, list(rows)))


# ----------------------------------------------------------------------------- invalidation
async def _dependents(db: AsyncSession, seeds: set[UUID]) -> set[UUID]:
    out, frontier = set(seeds), set(seeds)
    while frontier:
        nxt = set(await db.scalars(select(m.BlockDependency.block_id).where(
            m.BlockDependency.depends_on_block_id.in_(frontier))))
        frontier = nxt - out
        out |= nxt
    return out - seeds


async def invalidate(db: AsyncSession, revision_id: UUID, edited: set[UUID]) -> set[UUID]:
    """Blocks depending on `edited` (transitively) and their direct parents: APPROVED -> REVIEW_AGAIN."""
    targets = await _dependents(db, edited)
    targets |= {p for p in await db.scalars(select(m.ContentBlock.parent_id).where(
        m.ContentBlock.id.in_(edited), m.ContentBlock.parent_id.is_not(None))) if p is not None}
    targets -= edited
    changed = set(await db.scalars(
        update(m.ContentBlock).where(
            m.ContentBlock.id.in_(targets), m.ContentBlock.revision_id == revision_id,
            m.ContentBlock.deleted_at.is_(None), m.ContentBlock.review_status == "APPROVED")
        .values(review_status="REVIEW_AGAIN", version=m.ContentBlock.version + 1)
        .returning(m.ContentBlock.id)))
    return changed


def _status_after_edit(status: str) -> str:
    if status == "APPROVED":
        return "REVIEW_AGAIN"
    if status in ("AUTO_CHECKED", "FLAGGED"):
        return "UNREVIEWED"  # result belongs to the old hash; validation (phase 7) reruns
    return status


async def _record_edit(
    db: AsyncSession, user: CurrentUser, block: m.ContentBlock, *, payload: dict[str, Any] | None = None,
    no_source_reason: Any = _KEEP,
) -> None:
    before = block.content_hash
    new_payload = block.payload if payload is None else payload
    reason = block.no_source_reason if no_source_reason is _KEEP else no_source_reason
    transformation = "PARAPHRASED" if block.transformation == "ORIGINAL" and payload is not None else block.transformation
    after = content_hash(block.kind, new_payload, str(block.parent_id) if block.parent_id else None,
                         transformation, reason)
    await db.execute(update(m.ContentBlock).where(m.ContentBlock.id == block.id).values(
        payload=new_payload, no_source_reason=reason, transformation=transformation, content_hash=after,
        review_status=_status_after_edit(block.review_status), version=m.ContentBlock.version + 1))
    await db.execute(insert(m.TransformationEvent), [{
        "block_id": block.id, "actor_type": "TEACHER", "actor_id": user.id, "operation": "EDIT",
        "before_hash": before, "after_hash": after, "generator_version": None}])
    await invalidate(db, block.revision_id, {block.id})
    await db.commit()
    await db.refresh(block)


def _check_version(block: m.ContentBlock, version: int) -> None:
    if block.version != version:
        raise ApiError(409, "VERSION_CONFLICT", "Khối đã thay đổi, hãy tải lại")


# ----------------------------------------------------------------------------- write operations
async def patch_block(db: AsyncSession, user: CurrentUser, block_id: UUID, raw_payload: Any, version: int) -> BlockOut:
    block = await block_for(db, user, block_id, write=True)
    _check_version(block, version)
    payload = normalize_payload(block.kind, raw_payload)
    if payload == block.payload:
        return (await blocks_out(db, [block]))[0]
    await _record_edit(db, user, block, payload=payload)
    return (await blocks_out(db, [block]))[0]


async def set_competency(db: AsyncSession, user: CurrentUser, block_id: UUID, code: str | None) -> BlockOut:
    """Competency is metadata of the block: it is not part of the content hash, so no review is reset."""
    block = await block_for(db, user, block_id, write=True)
    known = await db.scalar(select(m.SubjectCompetency.code).where(m.SubjectCompetency.code == code).limit(1))
    if code is not None and known is None:
        raise ApiError(422, "INVALID_COMPETENCY", "Mã năng lực không có trong danh mục")
    await db.execute(update(m.ContentBlock).where(m.ContentBlock.id == block.id).values(competency_code=code, objective_id=None))
    await db.commit()
    await db.refresh(block)
    return (await blocks_out(db, [block]))[0]


async def create_block(db: AsyncSession, user: CurrentUser, revision_id: UUID, body: BlockCreate, raw_payload: Any) -> BlockOut:
    rev = await revision_for(db, user, revision_id, write=True)
    payload = normalize_payload(body.kind, raw_payload)
    parent = None
    if body.parent_id is not None:
        parent = await db.scalar(select(m.ContentBlock).where(
            m.ContentBlock.id == body.parent_id, m.ContentBlock.revision_id == rev.id,
            m.ContentBlock.deleted_at.is_(None)).with_for_update())
        if parent is None:
            raise ApiError(422, "PARENT_NOT_FOUND", "Khối cha không tồn tại trong bản này")
    top = await db.scalar(select(func.coalesce(func.max(m.ContentBlock.position), 0)).where(
        m.ContentBlock.revision_id == rev.id, m.ContentBlock.deleted_at.is_(None))) or 0
    pos = top + 1 if body.position is None or body.position > top else max(body.position, 1)
    if pos <= top:  # make room
        await db.execute(update(m.ContentBlock).where(
            m.ContentBlock.revision_id == rev.id, m.ContentBlock.deleted_at.is_(None),
            m.ContentBlock.position >= pos).values(position=m.ContentBlock.position + 1))
    h = content_hash(body.kind, payload, str(body.parent_id) if body.parent_id else None, "TEACHER_AUTHORED", None)
    block = m.ContentBlock(revision_id=rev.id, kind=body.kind, parent_id=body.parent_id, position=pos, payload=payload,
                           content_hash=h, transformation="TEACHER_AUTHORED", no_source_reason=None,
                           is_factual=body.is_factual)
    db.add(block)
    await db.flush()
    await db.execute(insert(m.TransformationEvent), [{
        "block_id": block.id, "actor_type": "TEACHER", "actor_id": user.id, "operation": "EDIT",
        "before_hash": None, "after_hash": h, "generator_version": None}])
    if parent is not None and body.kind in _DEP_KIND:
        target = parent.id
        if body.kind == "explanation":
            key = await db.scalar(select(m.ContentBlock.id).where(
                m.ContentBlock.parent_id == parent.id, m.ContentBlock.kind == "answer_key",
                m.ContentBlock.deleted_at.is_(None)).limit(1))
            target = key or parent.id
        await db.execute(insert(m.BlockDependency), [{
            "block_id": block.id, "depends_on_block_id": target, "kind": _DEP_KIND[body.kind]}])
    if parent is not None:  # a new child changes what the parent means
        await db.execute(update(m.ContentBlock).where(
            m.ContentBlock.id == parent.id, m.ContentBlock.review_status == "APPROVED").values(
            review_status="REVIEW_AGAIN", version=m.ContentBlock.version + 1))
    await db.commit()
    await db.refresh(block)
    return (await blocks_out(db, [block]))[0]


async def delete_block(db: AsyncSession, user: CurrentUser, block_id: UUID) -> None:
    block = await block_for(db, user, block_id, write=True)
    ids = {block.id}
    frontier = {block.id}
    while frontier:  # children go with their parent
        kids = set(await db.scalars(select(m.ContentBlock.id).where(
            m.ContentBlock.parent_id.in_(frontier), m.ContentBlock.deleted_at.is_(None))))
        frontier = kids - ids
        ids |= kids
    await db.execute(update(m.ContentBlock).where(m.ContentBlock.id.in_(ids)).values(
        deleted_at=func.now(), version=m.ContentBlock.version + 1))
    await invalidate(db, block.revision_id, ids)
    await db.commit()


# ----------------------------------------------------------------------------- provenance
async def current_source_hashes(db: AsyncSession, block_id: UUID) -> list[str]:
    rows = (await db.execute(
        select(m.SourceRevision.sha256, m.SourceAnchor.excerpt_hash)
        .select_from(m.ProvenanceLink)
        .join(m.SourceAnchor, m.SourceAnchor.id == m.ProvenanceLink.anchor_id)
        .join(m.SourceRevision, m.SourceRevision.id == m.SourceAnchor.source_revision_id)
        .where(m.ProvenanceLink.block_id == block_id, m.ProvenanceLink.status == "VERIFIED"))).all()
    return source_hashes([r[0] for r in rows], [r[1] for r in rows])


async def get_provenance(db: AsyncSession, user: CurrentUser, block_id: UUID) -> ProvenanceOut:
    block = await block_for(db, user, block_id, write=False)
    audit(db, user.id, "INSPECT_PROVENANCE", "content_block", block.id)  # no content
    link_rows = (await db.execute(
        select(m.ProvenanceLink, m.SourceAnchor, m.SourceRevision, m.SourceAsset)
        .join(m.SourceAnchor, m.SourceAnchor.id == m.ProvenanceLink.anchor_id)
        .join(m.SourceRevision, m.SourceRevision.id == m.SourceAnchor.source_revision_id)
        .join(m.SourceAsset, m.SourceAsset.id == m.SourceRevision.asset_id)
        .where(m.ProvenanceLink.block_id == block.id).order_by(m.SourceAnchor.code))).all()
    links = [ProvenanceLinkOut(
        id=lk.id, relation=lk.relation, rationale=lk.rationale, status=lk.status,
        anchor=AnchorRef(anchor_id=a.id, code=a.code, kind=a.kind, locator=a.locator, excerpt=a.excerpt,
                         source_revision_id=sr.id, source_title=asset.title, source_version=sr.version))
        for lk, a, sr, asset in link_rows]
    events = (await db.scalars(select(m.TransformationEvent).where(m.TransformationEvent.block_id == block.id)
                               .order_by(m.TransformationEvent.created_at))).all()
    vals = (await db.scalars(select(m.ValidationResult).where(m.ValidationResult.block_id == block.id)
                             .order_by(m.ValidationResult.created_at))).all()
    revs = (await db.execute(select(m.ReviewEvent, m.AppUser.display_name)
                             .join(m.AppUser, m.AppUser.id == m.ReviewEvent.reviewer_id)
                             .where(m.ReviewEvent.block_id == block.id)
                             .order_by(m.ReviewEvent.created_at))).all()
    now_sources = await current_source_hashes(db, block.id)
    last = revs[-1][0].id if revs else None
    out = ProvenanceOut(
        block=(await blocks_out(db, [block]))[0], links=links,
        events=[TransformationEventOut(
            id=e.id, actor_type=e.actor_type, actor_id=e.actor_id, operation=e.operation,
            before_hash=e.before_hash, after_hash=e.after_hash, generator_version=e.generator_version,
            created_at=e.created_at) for e in events],
        validations=[ValidationResultOut(
            id=v.id, rule=v.rule, severity=v.severity, outcome=v.outcome, evidence=v.evidence, method=v.method,
            content_hash=v.content_hash, is_current=v.content_hash == block.content_hash, created_at=v.created_at)
            for v in vals],
        reviews=[ReviewEventOut(
            id=r.id, action=r.action, content_hash=r.content_hash, source_hashes=r.source_hashes,
            reviewer_id=r.reviewer_id, reviewer_name=name, note=r.note, created_at=r.created_at,
            is_valid=(r.id == last and r.action == "APPROVE" and r.content_hash == block.content_hash
                      and sorted(r.source_hashes) == now_sources)) for r, name in revs])
    await db.commit()  # persists the audit entry
    return out


async def put_provenance(db: AsyncSession, user: CurrentUser, block_id: UUID, body: ProvenanceUpdate) -> ProvenanceOut:
    block = await block_for(db, user, block_id, write=True)
    _check_version(block, body.version)
    if (body.links is None) == (body.no_source_reason is None):
        raise ApiError(422, "PROVENANCE_INVALID", "Gửi links hoặc noSourceReason (một trong hai)")
    if body.links is not None:
        if not body.links:
            raise ApiError(422, "PROVENANCE_INVALID", "links không được rỗng")
        wanted = {lk.anchor_id for lk in body.links}
        ok = set(await db.scalars(  # PR-06: the server verifies; LLM-supplied ids are never trusted
            select(m.SourceAnchor.id)
            .join(m.LessonSource, m.LessonSource.source_revision_id == m.SourceAnchor.source_revision_id)
            .where(m.LessonSource.lesson_revision_id == block.revision_id, m.SourceAnchor.id.in_(wanted))))
        if ok != wanted:
            raise ApiError(422, "ANCHOR_NOT_IN_LESSON", "Có nguồn không thuộc bài giảng này")
        await db.execute(delete(m.ProvenanceLink).where(m.ProvenanceLink.block_id == block.id))
        seen: set[UUID] = set()
        rows = []
        for lk in body.links:
            if lk.anchor_id not in seen:
                seen.add(lk.anchor_id)
                rows.append({"block_id": block.id, "anchor_id": lk.anchor_id, "relation": lk.relation,
                             "rationale": lk.rationale, "status": "VERIFIED"})
        await db.execute(insert(m.ProvenanceLink), rows)
        await _record_edit(db, user, block, no_source_reason=None)
    else:
        reason = (body.no_source_reason or "").strip()
        if not reason:
            raise ApiError(422, "PROVENANCE_INVALID", "noSourceReason không được trống")
        await db.execute(delete(m.ProvenanceLink).where(m.ProvenanceLink.block_id == block.id))
        await _record_edit(db, user, block, no_source_reason=reason)
    return await get_provenance(db, user, block_id)
