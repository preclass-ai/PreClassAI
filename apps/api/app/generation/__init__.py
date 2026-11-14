"""Generation jobs (GĐ7): async in-process job, one worker, never approves anything (PR-09/PR-10).

Flow: anchors -> alias prompt -> provider -> parse -> server maps aliases to anchors (unknown ones are dropped and
logged as VAL-01 FAIL) -> blocks/links/dependencies/events -> validation -> AUTO_CHECKED or FLAGGED.
shortcut: jobs live in this process; a restart marks RUNNING jobs FAILED("restart") instead of resuming them.
"""

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.blocks import _DEP_KIND, normalize_payload
from app.config import get_settings
from app.db import models as m
from app.db.session import get_engine
from app.errors import ApiError
from app.generation.providers import (
    PROMPT_VERSION,
    AnchorView,
    Draft,
    DraftBlock,
    GenRequest,
    LLMProvider,
    ProviderFormatError,
    ProviderResult,
    get_provider,
)
from app.hashing import content_hash
from app.schemas import GenerateRequest, JobOut
from app.validation import validate_revision

JobRunner = Callable[[UUID], Awaitable[None]]
_TRANSFORMS = {"ORIGINAL", "PARAPHRASED", "SYNTHESISED", "AI_PROPOSED"}  # the model never claims TEACHER_AUTHORED
_tasks: set[asyncio.Task[None]] = set()


# ----------------------------------------------------------------------------- API-facing
async def create_job(db: AsyncSession, user_id: UUID, lesson_id: UUID, body: GenerateRequest) -> UUID:
    cfg = get_settings()
    if not cfg.ai_enabled:
        raise ApiError(503, "AI_DISABLED", "Tính năng AI đang tắt")
    used = await db.scalar(select(func.coalesce(func.sum(m.UsageDaily.tokens), 0)).where(
        m.UsageDaily.day == datetime.now(UTC).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)))
    if (used or 0) >= cfg.generation_daily_token_budget:
        raise ApiError(503, "AI_DISABLED", "Đã hết ngân sách AI trong ngày")
    rev = await db.scalar(
        select(m.LessonRevision).join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id)
        .where(m.Lesson.id == lesson_id, m.Lesson.author_id == user_id)
        .order_by(m.LessonRevision.revision_no.desc()).limit(1).with_for_update(of=m.LessonRevision))
    if rev is None:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy")
    if rev.state in ("PUBLISHED", "SUPERSEDED"):
        raise ApiError(409, "REVISION_LOCKED", "Bản này không còn sửa được")
    if await db.scalar(select(m.GenerationJob.id).where(
            m.GenerationJob.revision_id == rev.id, m.GenerationJob.status.in_(("QUEUED", "RUNNING")))):
        raise ApiError(409, "JOB_ALREADY_RUNNING", "Đang có tác vụ tạo nội dung cho bản này")
    has_blocks = await db.scalar(select(m.ContentBlock.id).where(
        m.ContentBlock.revision_id == rev.id, m.ContentBlock.deleted_at.is_(None)).limit(1))
    if has_blocks and body.mode == "initial":
        raise ApiError(409, "REVISION_NOT_EMPTY", "Bản đã có nội dung; dùng mode=append")
    job = m.GenerationJob(revision_id=rev.id, output_type=body.output_type, created_by=user_id, status="QUEUED",
                          params={"nItems": body.n_items, "focusSkills": list(body.focus_skills), "mode": body.mode})
    db.add(job)
    try:
        await db.commit()
    except IntegrityError as e:  # lost a race on the one-active-job-per-revision index
        await db.rollback()
        raise ApiError(409, "JOB_ALREADY_RUNNING", "Đang có tác vụ tạo nội dung cho bản này") from e
    return job.id


async def get_job(db: AsyncSession, user_id: UUID, job_id: UUID) -> JobOut:
    row = (await db.execute(
        select(m.GenerationJob).join(m.LessonRevision, m.LessonRevision.id == m.GenerationJob.revision_id)
        .join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id)
        .where(m.GenerationJob.id == job_id, m.Lesson.author_id == user_id))).scalar_one_or_none()
    if row is None:
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy")
    return JobOut(id=row.id, revision_id=row.revision_id, output_type=row.output_type,
                  status=row.status, error=row.error, block_count=int(row.params.get("blockCount", 0)),
                  model=row.model, created_at=row.created_at)


def background_runner() -> JobRunner:
    """Default runner: fire-and-forget in this process with its own DB session."""

    async def run(job_id: UUID) -> None:
        async def _go() -> None:
            async with async_sessionmaker(get_engine(), expire_on_commit=False)() as s:
                await run_job(s, job_id)

        t = asyncio.create_task(_go())
        _tasks.add(t)
        t.add_done_callback(_tasks.discard)

    return run


async def recover_after_restart() -> int:
    """RUNNING/QUEUED jobs cannot survive a restart (single in-process worker)."""
    async with async_sessionmaker(get_engine())() as s:
        res = await s.execute(update(m.GenerationJob).where(m.GenerationJob.status.in_(("RUNNING", "QUEUED")))
                              .values(status="FAILED", error="restart"))
        await s.commit()
        return int(res.rowcount or 0)  # type: ignore[attr-defined]


# ----------------------------------------------------------------------------- worker
async def _anchor_views(db: AsyncSession, revision_id: UUID) -> tuple[list[AnchorView], dict[str, UUID]]:
    rows = (await db.execute(
        select(m.SourceAnchor).join(m.LessonSource, m.LessonSource.source_revision_id == m.SourceAnchor.source_revision_id)
        .where(m.LessonSource.lesson_revision_id == revision_id)
        .order_by(m.SourceAnchor.source_revision_id, m.SourceAnchor.code))).scalars().all()
    views = [AnchorView(f"A{i}", a.code, a.kind, a.locator, a.excerpt, list(a.numbers)) for i, a in enumerate(rows, 1)]
    return views, {v.alias: a.id for v, a in zip(views, rows, strict=True)}


def _map_operands(payload: dict[str, Any], alias_code: dict[str, str]) -> dict[str, Any]:
    d = payload.get("derivation")
    if isinstance(d, dict) and isinstance(d.get("operands"), list):
        payload = {**payload, "derivation": {**d, "operands": [alias_code.get(o, o) if isinstance(o, str) else o
                                                              for o in d["operands"]]}}
    return payload


async def _persist(db: AsyncSession, rev: m.LessonRevision, draft: Draft, views: list[AnchorView],
                   alias_id: dict[str, UUID], generator: str) -> int:
    alias_code = {v.alias: v.code for v in views}
    top = await db.scalar(select(func.coalesce(func.max(m.ContentBlock.position), 0)).where(
        m.ContentBlock.revision_id == rev.id, m.ContentBlock.deleted_at.is_(None))) or 0
    ids: dict[str, UUID] = {}
    rows: list[dict[str, Any]] = []
    kept: list[tuple[DraftBlock, UUID, str]] = []
    for db_ in draft.blocks:
        if db_.key in ids or (db_.parentKey is not None and db_.parentKey not in ids):
            continue  # duplicate key, or its parent was dropped
        try:
            payload = normalize_payload(db_.kind, _map_operands(db_.payload, alias_code))
        except ApiError:
            continue  # malformed block from the model is dropped, never repaired silently
        transformation = db_.transformation if db_.transformation in _TRANSFORMS else "AI_PROPOSED"
        bid = uuid.uuid4()
        ids[db_.key] = bid
        parent = ids.get(db_.parentKey) if db_.parentKey else None
        h = content_hash(db_.kind, payload, str(parent) if parent else None, transformation, db_.noSourceReason)
        top += 1
        rows.append({"id": bid, "revision_id": rev.id, "kind": db_.kind, "parent_id": parent, "position": top,
                     "payload": payload, "content_hash": h, "transformation": transformation,
                     "no_source_reason": db_.noSourceReason, "is_factual": db_.isFactual})
        kept.append((db_, bid, h))
    if not rows:
        return 0
    await db.execute(insert(m.ContentBlock), rows)
    links, dropped, deps = [], [], []
    for d, bid, _ in kept:
        seen: set[UUID] = set()
        for alias in d.anchorAliases:
            aid = alias_id.get(alias)  # PR-06: unknown / foreign ids are never trusted
            if aid is None:
                dropped.append(bid)
            elif aid not in seen:
                seen.add(aid)
                links.append({"block_id": bid, "anchor_id": aid, "relation": "quotes" if d.transformation == "ORIGINAL"
                              else "derived_from", "status": "VERIFIED"})
        parent = ids.get(d.parentKey) if d.parentKey else None
        if parent is not None and d.kind in _DEP_KIND:
            target = parent
            if d.kind == "explanation":
                key = next((i for dd, i, _ in kept if dd.parentKey == d.parentKey and dd.kind == "answer_key"), None)
                target = key or parent
            deps.append({"block_id": bid, "depends_on_block_id": target, "kind": _DEP_KIND[d.kind]})
    if links:
        await db.execute(insert(m.ProvenanceLink), links)
    if deps:
        await db.execute(insert(m.BlockDependency), deps)
    await db.execute(insert(m.TransformationEvent), [{
        "block_id": bid, "actor_type": "AI", "operation": "GENERATE", "before_hash": None, "after_hash": h,
        "generator_version": generator} for _, bid, h in kept])
    if dropped:  # AT-02: the invalid anchor id is dropped and the drop is recorded
        by_block: dict[UUID, int] = {}
        for b in dropped:
            by_block[b] = by_block.get(b, 0) + 1
        hashes = {bid: h for _, bid, h in kept}
        await db.execute(insert(m.ValidationResult), [{
            "block_id": b, "rule": "VAL-01", "severity": "BLOCKER", "outcome": "FAIL",
            "evidence": {"droppedAnchors": n}, "method": "generation", "content_hash": hashes[b]}
            for b, n in by_block.items()])
    return len(rows)


async def _call(provider: LLMProvider, req: GenRequest) -> ProviderResult:
    try:
        return await provider.generate(req)
    except ProviderFormatError:
        return await provider.generate(req)  # one retry on invalid JSON


async def run_job(db: AsyncSession, job_id: UUID) -> None:
    job = await db.get(m.GenerationJob, job_id)
    if job is None:
        return
    job.status = "RUNNING"
    await db.commit()
    try:
        cfg = get_settings()
        provider = get_provider(cfg.llm_provider, cfg.mock_inject)
        if provider is None:
            raise ApiError(503, "AI_DISABLED", "Nhà cung cấp AI chưa được cấu hình")
        rev = await db.get(m.LessonRevision, job.revision_id)
        lesson = await db.get(m.Lesson, rev.lesson_id) if rev else None
        if rev is None or lesson is None:
            raise ApiError(404, "NOT_FOUND", "Không tìm thấy")
        views, alias_id = await _anchor_views(db, rev.id)
        req = GenRequest(lesson.grade, job.output_type, int(job.params.get("nItems", 5)),
                         list(job.params.get("focusSkills", [])), views)
        result = await _call(provider, req)
        n = await _persist(db, rev, result.draft, views, alias_id, f"{result.model}/{PROMPT_VERSION}")
        await db.commit()
        await validate_revision(db, rev.id)  # AUTO_CHECKED or FLAGGED; never APPROVED
        job = await db.get(m.GenerationJob, job_id)
        assert job is not None  # noqa: S101
        job.status, job.error, job.model, job.prompt_version = "SUCCEEDED", None, result.model, PROMPT_VERSION
        job.tokens_in, job.tokens_out = result.tokens_in, result.tokens_out
        job.params = {**job.params, "blockCount": n}
        day = datetime.now(UTC).replace(tzinfo=None, hour=0, minute=0, second=0, microsecond=0)
        await db.execute(pg_insert(m.UsageDaily).values(day=day, tokens=result.tokens_in + result.tokens_out)
                         .on_conflict_do_update(index_elements=["day"],
                                                set_={"tokens": m.UsageDaily.tokens + result.tokens_in + result.tokens_out}))
        await db.commit()
    except Exception as e:  # noqa: BLE001 the job must always end in a terminal state
        await db.rollback()
        failed = await db.get(m.GenerationJob, job_id)
        if failed is not None:
            failed.status = "FAILED"
            failed.error = (e.code if isinstance(e, ApiError) else type(e).__name__)[:200]  # never any content
            await db.commit()
