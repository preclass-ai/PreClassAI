# ruff: noqa: E501
"""Lesson plans (CV 5512) for the teacher: upload, check what was read, confirm answers, build the pre-class lesson draft.

The draft goes through the normal pipeline: blocks are written with provenance links to the plan's anchors, validation
VAL-01..10 runs, and nothing is approved or published here.
"""

import uuid
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.blocks import NOT_FOUND
from app.config import get_settings
from app.db import models as m
from app.errors import ApiError
from app.generation import _persist
from app.generation.providers import AnchorView, Draft, DraftBlock
from app.lessonplan.model import PlanFile
from app.schemas import (
    PlanDetail,
    PlanItem,
    PlanLessonOut,
    PlanList,
    PlanMcq,
    PlanMcqOption,
    PlanObjective,
    PlanOut,
    PlanSection,
)
from app.sources.formats import MIME, Limits, detect_kind, parse_isolated
from app.sources.parse import MAX_UPLOAD_BYTES, ParsedAnchor
from app.sources.service import _insert_revision, _store_docx, sha256_hex_bytes
from app.validation import validate_revision

PLAN_TIMEOUT_S = 120  # pdfminer reads about 0.5 s per page
VN_OFFSET = timedelta(hours=7)
MAX_PRACTICE = 5


def due_before(taught_from: date | None) -> datetime | None:
    """Day before the first teaching day at 23:59 Vietnam time (UTC+7), as an aware UTC datetime."""
    if taught_from is None:
        return None
    local = datetime.combine(taught_from - timedelta(days=1), time(23, 59))
    return (local - VN_OFFSET).replace(tzinfo=UTC)


async def _own(db: AsyncSession, user: CurrentUser, plan_id: UUID) -> m.LessonPlan:
    plan = await db.scalar(select(m.LessonPlan).where(m.LessonPlan.id == plan_id, m.LessonPlan.owner_id == user.id))
    if plan is None:
        raise NOT_FOUND
    return plan


async def upload(db: AsyncSession, user: CurrentUser, data: bytes) -> PlanList:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", "Tệp vượt quá 10 MB")
    kind = detect_kind(data)
    if kind not in ("pdf", "docx"):
        raise ApiError(422, "UNSUPPORTED_FILE", "Giáo án cần là tệp DOCX hoặc PDF có chữ")
    cfg = get_settings()
    lim = Limits(cfg.source_max_pdf_pages, cfg.source_max_xlsx_sheets, cfg.source_max_xlsx_cells, cfg.source_max_pptx_slides,
                 PLAN_TIMEOUT_S, cfg.source_parse_mem_mb)
    plan: PlanFile = await parse_isolated("plan", data, lim)
    if not plan.anchors or not plan.lessons:
        raise ApiError(422, "EMPTY_SOURCE", "Không đọc được nội dung giáo án")
    title = next((x.title for x in plan.lessons if x.title), "Giáo án")
    asset = m.SourceAsset(owner_id=user.id, title=f"Giáo án: {title}"[:200], license_note=None, visibility="PRIVATE")
    db.add(asset)
    await db.flush()
    anchors = [ParsedAnchor(a.kind, {**a.locator}, a.excerpt) for a in plan.anchors]
    rev = await _insert_revision(db, asset.id, 1, sha256_hex_bytes(data), MIME[kind], _store_docx(data, kind), anchors)
    codes = (await db.execute(select(m.SourceAnchor.code, m.SourceAnchor.id).where(m.SourceAnchor.source_revision_id == rev.id))).all()
    ids: list[UUID] = [uuid.UUID(int=0)] * len(anchors)
    for code, aid in codes:
        ids[int(code.rsplit("_", 1)[1]) - 1] = aid
    out: list[UUID] = []
    for les in plan.lessons:
        row = m.LessonPlan(
            owner_id=user.id, source_revision_id=rev.id, subject=les.subject or "UNKNOWN", grade=les.grade,
            title=(les.title or "Giáo án")[:200], ppct_period=les.ppct_period, week=les.week, planned_on=les.planned_on,
            taught_from=les.taught_from, taught_to=les.taught_to, redacted_count=les.redacted)
        db.add(row)
        await db.flush()
        out.append(row.id)
        for pos, sec in enumerate(les.sections, 1):
            await db.execute(insert(m.LessonSection).values(
                lesson_plan_id=row.id, position=pos, kind=sec.kind, activity_type=sec.activity_type, sub=sec.sub,
                anchor_ids=[ids[i] for i in sec.anchors]))
        for ob in les.objectives:
            await db.execute(insert(m.Objective).values(
                lesson_plan_id=row.id, text=ob.text[:1500], competency_code=ob.competency_code, anchor_id=ids[ob.anchor]))
        for pos, q in enumerate(les.mcqs, 1):
            await db.execute(insert(m.ExtractedMcq).values(
                lesson_plan_id=row.id, position=pos, stem_anchor_id=ids[q.stem], option_anchor_ids=[ids[i] for i in q.options],
                correct_option=q.correct, answer_source=q.answer_source, confidence=q.confidence,
                needs_confirmation=q.needs_confirmation))
    await db.commit()
    return PlanList(items=[await _out(db, await _own(db, user, i)) for i in out])


async def _lesson_of(db: AsyncSession, p: m.LessonPlan) -> UUID | None:
    """The pre-class lesson built from this plan: the author's lesson that cites the plan's source revision and carries its title."""
    return await db.scalar(
        select(m.Lesson.id).join(m.LessonRevision, m.LessonRevision.lesson_id == m.Lesson.id)
        .join(m.LessonSource, m.LessonSource.lesson_revision_id == m.LessonRevision.id)
        .where(m.LessonSource.source_revision_id == p.source_revision_id, m.Lesson.author_id == p.owner_id,
               m.Lesson.title == f"Chuẩn bị: {p.title}"[:200]).limit(1))


async def _out(db: AsyncSession, p: m.LessonPlan) -> PlanOut:
    secs = (await db.scalars(select(m.LessonSection).where(m.LessonSection.lesson_plan_id == p.id))).all()
    mcqs = (await db.scalars(select(m.ExtractedMcq).where(m.ExtractedMcq.lesson_plan_id == p.id))).all()
    return PlanOut(
        id=p.id, title=p.title, subject=p.subject, grade=p.grade, ppct_period=p.ppct_period, week=p.week,
        taught_from=p.taught_from, taught_to=p.taught_to, suggested_due_at=due_before(p.taught_from),
        redacted_count=p.redacted_count,
        activities=sorted({s.activity_type for s in secs if s.kind == "activity" and s.activity_type}),
        mcq_count=len(mcqs), needs_confirmation_count=sum(1 for q in mcqs if q.needs_confirmation),
        lesson_id=await _lesson_of(db, p))


async def list_plans(db: AsyncSession, user: CurrentUser) -> PlanList:
    rows = (await db.scalars(select(m.LessonPlan).where(m.LessonPlan.owner_id == user.id).order_by(
        m.LessonPlan.created_at.desc(), m.LessonPlan.title))).all()
    return PlanList(items=[await _out(db, p) for p in rows])


async def _anchors(db: AsyncSession, ids: set[UUID]) -> dict[UUID, m.SourceAnchor]:
    if not ids:
        return {}
    rows = (await db.scalars(select(m.SourceAnchor).where(m.SourceAnchor.id.in_(ids)))).all()
    return {a.id: a for a in rows}


async def get_plan(db: AsyncSession, user: CurrentUser, plan_id: UUID) -> PlanDetail:
    p = await _own(db, user, plan_id)
    secs = (await db.scalars(select(m.LessonSection).where(m.LessonSection.lesson_plan_id == p.id).order_by(m.LessonSection.position))).all()
    objs = (await db.scalars(select(m.Objective).where(m.Objective.lesson_plan_id == p.id))).all()
    mcqs = (await db.scalars(select(m.ExtractedMcq).where(m.ExtractedMcq.lesson_plan_id == p.id).order_by(m.ExtractedMcq.position))).all()
    want = {a for s in secs for a in s.anchor_ids} | {q.stem_anchor_id for q in mcqs} | {a for q in mcqs for a in q.option_anchor_ids}
    by = await _anchors(db, want)
    names = {c.code: c.name_vi for c in (await db.scalars(select(m.SubjectCompetency).where(m.SubjectCompetency.subject == p.subject))).all()}

    def item(a: m.SourceAnchor) -> PlanItem:
        return PlanItem(anchor_id=a.id, page=a.locator.get("page"), type=str(a.locator.get("type", "paragraph")), text=a.excerpt)

    base = await _out(db, p)
    return PlanDetail(
        **base.model_dump(),
        sections=[PlanSection(kind=s.kind, activity_type=s.activity_type, sub=s.sub, items=[item(by[a]) for a in s.anchor_ids if a in by])
                  for s in secs],
        objectives=[PlanObjective(text=o.text, competency_code=o.competency_code, competency_name=names.get(o.competency_code or "")) for o in objs],
        mcqs=[PlanMcq(id=q.id, position=q.position, stem=by[q.stem_anchor_id].excerpt,
                      options=[PlanMcqOption(label=chr(65 + i), text=by[a].excerpt) for i, a in enumerate(q.option_anchor_ids)],
                      correct_option=q.correct_option, answer_source=q.answer_source, needs_confirmation=q.needs_confirmation)
              for q in mcqs])


async def set_answer(db: AsyncSession, user: CurrentUser, plan_id: UUID, mcq_id: UUID, option: str) -> PlanDetail:
    p = await _own(db, user, plan_id)
    q = await db.scalar(select(m.ExtractedMcq).where(m.ExtractedMcq.id == mcq_id, m.ExtractedMcq.lesson_plan_id == p.id))
    if q is None:
        raise NOT_FOUND
    if ord(option) - 65 >= len(q.option_anchor_ids):
        raise ApiError(422, "INVALID_OPTION", "Câu này không có phương án đó")
    await db.execute(update(m.ExtractedMcq).where(m.ExtractedMcq.id == q.id).values(
        correct_option=option, answer_source="teacher", confidence="high", needs_confirmation=False))
    await db.commit()
    return await get_plan(db, user, plan_id)


# ---------------------------------------------------------------- "Tạo bài chuẩn bị trước giờ học"
def _first(items: list[m.SourceAnchor], pred: Any) -> m.SourceAnchor | None:
    return next((a for a in items if pred(a)), None)


async def build_lesson(db: AsyncSession, user: CurrentUser, plan_id: UUID) -> PlanLessonOut:
    """Default mapping (the teacher edits the draft afterwards like any lesson):
    mở đầu -> 1 trigger question; hình thành -> up to 2 reading cards + 1 flashcard quoted verbatim; luyện tập -> up to 5
    confirmed MCQ with a templated explanation; vận dụng -> 1 after-class task. Everything is a draft to review."""
    p = await _own(db, user, plan_id)
    if await _lesson_of(db, p) is not None:
        raise ApiError(409, "LESSON_EXISTS", "Đã tạo bài chuẩn bị từ giáo án này")
    secs = (await db.scalars(select(m.LessonSection).where(m.LessonSection.lesson_plan_id == p.id).order_by(m.LessonSection.position))).all()
    mcqs = (await db.scalars(select(m.ExtractedMcq).where(m.ExtractedMcq.lesson_plan_id == p.id).order_by(m.ExtractedMcq.position))).all()
    want = {a for s in secs for a in s.anchor_ids} | {q.stem_anchor_id for q in mcqs} | {a for q in mcqs for a in q.option_anchor_ids}
    by = await _anchors(db, want)

    def anchors_of(kind: str) -> list[m.SourceAnchor]:
        return [by[a] for s in secs if s.activity_type == kind for a in s.anchor_ids if a in by and by[a].kind != "HEADING"]

    lesson = m.Lesson(author_id=user.id, grade=p.grade if p.grade in (10, 11) else 10, title=f"Chuẩn bị: {p.title}"[:200],
                      goal="Bài chuẩn bị trước giờ học, dựng từ giáo án.")
    db.add(lesson)
    await db.flush()
    rev = m.LessonRevision(lesson_id=lesson.id, revision_no=1, state="DRAFT")
    db.add(rev)
    await db.flush()
    await db.execute(insert(m.LessonSource).values(lesson_revision_id=rev.id, source_revision_id=p.source_revision_id))
    ordered = list(by.values())
    views = [AnchorView(f"A{i}", a.code, a.kind, a.locator, a.excerpt, list(a.numbers)) for i, a in enumerate(ordered, 1)]
    alias = {a.id: v.alias for v, a in zip(views, ordered, strict=True)}
    alias_id = {v.alias: a.id for v, a in zip(views, ordered, strict=True)}
    blocks: list[DraftBlock] = []

    def add(key: str, kind: str, payload: dict[str, Any], anchor: m.SourceAnchor, *, parent: str | None = None,
            tr: str = "ORIGINAL", factual: bool = False) -> None:
        blocks.append(DraftBlock(key=key, kind=kind, parentKey=parent, payload=payload, transformation=tr,
                                 anchorAliases=[alias[anchor.id]], isFactual=factual))

    opening = anchors_of("mo_dau")
    trig = _first(opening, lambda a: a.excerpt.rstrip().endswith("?")) or _first(opening, lambda a: len(a.excerpt) > 20)
    if trig:
        add("open", "instruction", {"text": trig.excerpt}, trig)
    boxes = [a for a in anchors_of("hinh_thanh") if a.locator.get("type") == "knowledge_box"][:2]
    for i, b in enumerate(boxes, 1):
        add(f"read{i}", "paragraph", {"text": b.excerpt}, b, factual=True)
    if boxes:
        add("fc", "card_front", {"text": "Em nhớ gì về nội dung này?"}, boxes[0], tr="SYNTHESISED")
        add("fcb", "card_back", {"text": boxes[0].excerpt}, boxes[0], parent="fc")
    ok = [q for q in mcqs if not q.needs_confirmation and q.correct_option]
    chosen = ok[:MAX_PRACTICE]
    for n, q in enumerate(chosen, 1):
        stem = by[q.stem_anchor_id]
        opts = [by[a] for a in q.option_anchor_ids]
        add(f"q{n}", "worksheet_item", {"stem": stem.excerpt, "itemType": "MCQ", "skill": "EXPLAIN"}, stem)
        for i, o in enumerate(opts):
            add(f"q{n}{chr(97 + i)}", "option", {"label": chr(65 + i), "text": o.excerpt}, o, parent=f"q{n}")
        right = opts[ord(q.correct_option or "A") - 65]
        add(f"q{n}k", "answer_key", {"correct": q.correct_option}, right, parent=f"q{n}")  # the pipeline never lets a generator claim TEACHER_AUTHORED; the confirmed option is quoted
        add(f"q{n}e", "explanation", {"text": f"Đáp án đúng là {q.correct_option}. {right.excerpt}"}, right, parent=f"q{n}", tr="SYNTHESISED")
    apply = _first(anchors_of("van_dung"), lambda a: len(a.excerpt) > 20)
    if apply:
        add("apply", "instruction", {"text": apply.excerpt}, apply)
    n = await _persist(db, rev, Draft(blocks=blocks), views, alias_id, "plan-5512/1")
    await db.commit()
    await validate_revision(db, rev.id)
    return PlanLessonOut(lesson_id=lesson.id, blocks=n, practice_items=len(chosen),
                         skipped_unconfirmed=len(mcqs) - len(ok), left_for_after_class=max(0, len(ok) - MAX_PRACTICE))
