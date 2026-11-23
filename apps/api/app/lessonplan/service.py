# ruff: noqa: E501
"""Lesson plans (CV 5512) for the teacher: upload, check what was read, confirm answers, build the pre-class lesson draft.

The draft goes through the normal pipeline: blocks are written with provenance links to the plan's anchors, validation
VAL-01..10 runs, and nothing is approved or published here.
"""

import asyncio
import logging
import re
import uuid
from collections.abc import Awaitable, Callable
from datetime import UTC, date, datetime, time, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import CurrentUser
from app.blocks import NOT_FOUND
from app.config import get_settings
from app.db import models as m
from app.db.session import get_engine
from app.errors import ApiError
from app.generation import _persist
from app.generation.providers import AnchorView, Draft, DraftBlock
from app.habit import rules
from app.lessonplan import quizgen
from app.lessonplan.model import PlanFile
from app.schemas import (
    Competency,
    CompetencyList,
    PlanAiItemOut,
    PlanAiItemUpdate,
    PlanAiList,
    PlanAiRegenerate,
    PlanDetail,
    PlanItem,
    PlanJobLatest,
    PlanJobOut,
    PlanLessonOut,
    PlanList,
    PlanMcq,
    PlanMcqOption,
    PlanObjective,
    PlanOut,
    PlanSection,
    SubjectCompetencyOut,
)
from app.sources.formats import MIME, Limits, detect_kind, parse_isolated
from app.sources.numbers import parse_numbers
from app.sources.parse import MAX_UPLOAD_BYTES, ParsedAnchor
from app.sources.service import _insert_revision, _store_docx, sha256_hex_bytes
from app.validation import validate_revision

log = logging.getLogger(__name__)
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


# ---------------------------------------------------------------- background job: upload -> parse -> plans
PlanRunner = Callable[[UUID, bytes], Awaitable[None]]
PROGRESS: dict[UUID, tuple[int, int]] = {}  # job id -> (page, pages), in memory: a restart fails the job anyway
_tasks: set[asyncio.Task[None]] = set()
_ACTIVE = ("queued", "parsing")
# Default competency by activity (DIA_LI codes); only applied when the code exists in the plan's subject catalogue.
ACTIVITY_COMPETENCY = {"mo_dau": "NHAN_THUC", "hinh_thanh": "NHAN_THUC", "van_dung": "VAN_DUNG"}
_READS_DATA = re.compile(r"bảng|biểu đồ|bản đồ|át lát|atlat|số liệu|quan sát|dựa vào", re.IGNORECASE)


def plan_runner() -> PlanRunner:
    """Default runner: fire-and-forget in this process with its own DB session (tests override it to run inline)."""

    async def run(job_id: UUID, data: bytes) -> None:
        async def _go() -> None:
            async with async_sessionmaker(get_engine(), expire_on_commit=False)() as s:
                await run_job(s, job_id, data)

        t = asyncio.create_task(_go())
        _tasks.add(t)
        t.add_done_callback(_tasks.discard)

    return run


async def recover_after_restart() -> int:
    async with async_sessionmaker(get_engine())() as s:
        res = await s.execute(update(m.LessonPlanJob).where(m.LessonPlanJob.state.in_(_ACTIVE)).values(
            state="failed", error_code="RESTART", error_title="Máy chủ vừa khởi động lại. Em tải giáo án lên lần nữa nhé."))
        await s.commit()
        return int(res.rowcount or 0) + await quizgen.recover_after_restart()  # type: ignore[attr-defined]


def _job_out(j: m.LessonPlanJob) -> PlanJobOut:
    page, pages = PROGRESS.get(j.id, (0, 0)) if j.state == "parsing" else (0, 0)
    return PlanJobOut(id=j.id, state=j.state, file_name=j.file_name, page=page or None, pages=pages or None,
                      error_code=j.error_code, error_title=j.error_title, plan_ids=list(j.plan_ids), created_at=j.created_at)


async def start_upload(db: AsyncSession, user: CurrentUser, data: bytes, name: str | None, runner: PlanRunner) -> PlanJobOut:
    """Quick checks, one job row, and the parse runs in the background. One active job per teacher."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", "Tệp vượt quá 10 MB")
    kind = detect_kind(data)
    if kind not in ("pdf", "docx"):
        raise ApiError(422, "UNSUPPORTED_FILE", "Giáo án cần là tệp DOCX hoặc PDF có chữ")
    busy = await db.scalar(select(m.LessonPlanJob.id).where(m.LessonPlanJob.owner_id == user.id, m.LessonPlanJob.state.in_(_ACTIVE)).limit(1))
    if busy is not None:
        raise ApiError(409, "PARSE_BUSY", "Em đang có một giáo án được đọc. Đợi xong rồi tải tiếp nhé.")
    job = m.LessonPlanJob(owner_id=user.id, file_name=(name or "")[:200] or None)
    db.add(job)
    await db.commit()
    await runner(job.id, data)
    await db.refresh(job)
    return _job_out(job)


async def competencies(db: AsyncSession) -> CompetencyList:
    rows = (await db.scalars(select(m.SubjectCompetency).order_by(m.SubjectCompetency.subject, m.SubjectCompetency.code))).all()
    return CompetencyList(items=[SubjectCompetencyOut(subject=c.subject, code=c.code, name=c.name_vi) for c in rows])


async def latest_job(db: AsyncSession, user: CurrentUser) -> PlanJobLatest:
    j = await db.scalar(select(m.LessonPlanJob).where(m.LessonPlanJob.owner_id == user.id).order_by(m.LessonPlanJob.created_at.desc()).limit(1))
    return PlanJobLatest(job=_job_out(j) if j else None)


async def get_job(db: AsyncSession, user: CurrentUser, job_id: UUID) -> PlanJobOut:
    j = await db.scalar(select(m.LessonPlanJob).where(m.LessonPlanJob.id == job_id, m.LessonPlanJob.owner_id == user.id))
    if j is None:
        raise NOT_FOUND
    return _job_out(j)


async def _set_state(db: AsyncSession, job_id: UUID, **vals: Any) -> None:
    await db.execute(update(m.LessonPlanJob).where(m.LessonPlanJob.id == job_id).values(updated_at=func.clock_timestamp(), **vals))
    await db.commit()


async def run_job(db: AsyncSession, job_id: UUID, data: bytes) -> None:
    job = await db.get(m.LessonPlanJob, job_id)
    if job is None:
        return
    owner = job.owner_id
    cfg = get_settings()
    lim = Limits(cfg.source_max_pdf_pages, cfg.source_max_xlsx_sheets, cfg.source_max_xlsx_cells, cfg.source_max_pptx_slides,
                 cfg.plan_parse_timeout_s, cfg.source_parse_mem_mb)

    async def started() -> None:
        await _set_state(db, job_id, state="parsing")

    def progress(page: int, pages: int) -> None:
        PROGRESS[job_id] = (page, pages)

    try:
        plan: PlanFile = await parse_isolated("plan", data, lim, progress=progress, on_start=started)
        if not plan.anchors or not plan.lessons:
            raise ApiError(422, "EMPTY_SOURCE", "Không đọc được nội dung giáo án")
        ids = await _persist_plans(db, owner, plan, data)
        ai = cfg.quiz_gen_enabled
        if ai:
            await quizgen.mark_queued(db, ids)
        await _set_state(db, job_id, state="done", plan_ids=ids)
        if ai:
            await quizgen.run_all(db, ids)  # drafts after the plan is readable; a failure here never fails the job
    except ApiError as e:
        await db.rollback()
        await _set_state(db, job_id, state="failed", error_code=e.code, error_title=e.title)
    except Exception:  # noqa: BLE001 the teacher gets a friendly message, details stay in the server log
        log.exception("lesson plan job failed")
        await db.rollback()
        await _set_state(db, job_id, state="failed", error_code="PARSE_FAILED",
                         error_title="Chưa đọc được giáo án này. Em thử lại hoặc nạp bản DOCX nhé.")
    finally:
        PROGRESS.pop(job_id, None)


def default_competency(codes: set[str], text: str) -> str | None:
    """MCQ in the practice part: reading a table, chart or map -> TIM_HIEU, otherwise NHAN_THUC."""
    code = "TIM_HIEU" if _READS_DATA.search(text) else "NHAN_THUC"
    return code if code in codes else None


async def _persist_plans(db: AsyncSession, owner: UUID, plan: PlanFile, data: bytes) -> list[UUID]:
    kind = detect_kind(data)
    title = next((x.title for x in plan.lessons if x.title), "Giáo án")
    asset = m.SourceAsset(owner_id=owner, title=f"Giáo án: {title}"[:200], license_note=None, visibility="PRIVATE")
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
            owner_id=owner, source_revision_id=rev.id, subject=les.subject or "UNKNOWN", grade=les.grade,
            title=(les.title or "Giáo án")[:200], ppct_period=les.ppct_period, week=les.week, planned_on=les.planned_on,
            taught_from=les.taught_from, taught_to=les.taught_to, redacted_count=les.redacted)
        db.add(row)
        await db.flush()
        out.append(row.id)
        cat = set(await db.scalars(select(m.SubjectCompetency.code).where(m.SubjectCompetency.subject == row.subject)))
        for pos, sec in enumerate(les.sections, 1):
            await db.execute(insert(m.LessonSection).values(
                lesson_plan_id=row.id, position=pos, kind=sec.kind, activity_type=sec.activity_type, sub=sec.sub,
                anchor_ids=[ids[i] for i in sec.anchors]))
        for ob in les.objectives:
            await db.execute(insert(m.Objective).values(
                lesson_plan_id=row.id, text=ob.text[:1500], competency_code=ob.competency_code, anchor_id=ids[ob.anchor]))
        for pos, q in enumerate(les.mcqs, 1):
            text = " ".join(plan.anchors[i].excerpt for i in [q.stem, *q.options])
            await db.execute(insert(m.ExtractedMcq).values(
                lesson_plan_id=row.id, position=pos, stem_anchor_id=ids[q.stem], option_anchor_ids=[ids[i] for i in q.options],
                correct_option=q.correct, answer_source=q.answer_source, confidence=q.confidence,
                needs_confirmation=q.needs_confirmation, competency_code=default_competency(cat, text)))
    await db.commit()
    return out


async def _lesson_of(db: AsyncSession, p: m.LessonPlan) -> UUID | None:
    """The pre-class lesson built from this plan: the author's lesson that cites the plan's source revision and carries its title."""
    return await db.scalar(
        select(m.Lesson.id).join(m.LessonRevision, m.LessonRevision.lesson_id == m.Lesson.id)
        .join(m.LessonSource, m.LessonSource.lesson_revision_id == m.LessonRevision.id)
        .where(m.LessonSource.source_revision_id == p.source_revision_id, m.Lesson.author_id == p.owner_id,
               m.Lesson.lesson_plan_id == p.id).limit(1))


def default_title(plan_title: str) -> str:
    """The lesson's own title from the plan (\"Bài 4. Sự hình thành ...\"): no \"Chuẩn bị:\" prefix, first letter capital, 3 to 120 characters."""
    t = " ".join(re.sub(r"^\s*chuẩn bị\s*:\s*", "", plan_title, flags=re.I).split())[:120].strip()
    return t[:1].upper() + t[1:] if len(t) >= 3 else "Bài chuẩn bị trước giờ học"


async def _out(db: AsyncSession, p: m.LessonPlan) -> PlanOut:
    secs = (await db.scalars(select(m.LessonSection).where(m.LessonSection.lesson_plan_id == p.id))).all()
    mcqs = (await db.scalars(select(m.ExtractedMcq).where(m.ExtractedMcq.lesson_plan_id == p.id))).all()
    ai = (await db.scalars(select(m.PlanAiItem).where(m.PlanAiItem.lesson_plan_id == p.id, m.PlanAiItem.status != "rejected"))).all()
    return PlanOut(
        ai_state=p.ai_state, ai_stats=p.ai_stats, ai_quiz_count=sum(1 for i in ai if i.kind == "quiz"),
        ai_quiz_needs_confirmation_count=sum(1 for i in ai if i.kind == "quiz" and i.needs_confirmation),
        ai_review_count=sum(1 for i in ai if i.kind == "review"), ai_needs_confirmation_count=sum(1 for i in ai if i.needs_confirmation),
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
    cat = (await db.scalars(select(m.SubjectCompetency).where(m.SubjectCompetency.subject == p.subject).order_by(m.SubjectCompetency.code))).all()
    names = {c.code: c.name_vi for c in cat}

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
                      correct_option=q.correct_option, answer_source=q.answer_source, needs_confirmation=q.needs_confirmation,
                      competency_code=q.competency_code)
              for q in mcqs],
        competencies=[Competency(code=c.code, name=c.name_vi) for c in cat])


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


async def set_mcq_competency(db: AsyncSession, user: CurrentUser, plan_id: UUID, mcq_id: UUID, code: str | None) -> PlanDetail:
    p = await _own(db, user, plan_id)
    q = await db.scalar(select(m.ExtractedMcq).where(m.ExtractedMcq.id == mcq_id, m.ExtractedMcq.lesson_plan_id == p.id))
    if q is None:
        raise NOT_FOUND
    if code is not None and await db.get(m.SubjectCompetency, (p.subject, code)) is None:
        raise ApiError(422, "INVALID_COMPETENCY", "Mã năng lực này không có trong môn của giáo án")
    await db.execute(update(m.ExtractedMcq).where(m.ExtractedMcq.id == q.id).values(competency_code=code))
    await db.commit()
    return await get_plan(db, user, plan_id)


# ---------------------------------------------------------------- AI drafts: review, edit, regenerate
def _ai_out(i: m.PlanAiItem) -> PlanAiItemOut:
    return PlanAiItemOut(id=i.id, kind=i.kind, position=i.position, status=i.status, origin=i.origin,
                         payload=quizgen.clean_payload(i.kind, i.payload), source_quote=i.source_quote, needs_confirmation=i.needs_confirmation)


async def list_ai_items(db: AsyncSession, user: CurrentUser, plan_id: UUID) -> PlanAiList:
    p = await _own(db, user, plan_id)
    rows = (await db.scalars(select(m.PlanAiItem).where(m.PlanAiItem.lesson_plan_id == p.id).order_by(
        m.PlanAiItem.kind.desc(), m.PlanAiItem.position))).all()
    return PlanAiList(items=[_ai_out(i) for i in rows])


async def update_ai_item(db: AsyncSession, user: CurrentUser, plan_id: UUID, item_id: UUID, body: PlanAiItemUpdate) -> PlanAiItemOut:
    """Approve, reject or edit one draft. Editing sends it back to draft: the teacher approves what they last saw."""
    p = await _own(db, user, plan_id)
    it = await db.scalar(select(m.PlanAiItem).where(m.PlanAiItem.id == item_id, m.PlanAiItem.lesson_plan_id == p.id))
    if it is None:
        raise NOT_FOUND
    if await _lesson_of(db, p) is not None:
        raise ApiError(409, "LESSON_EXISTS", "Bài chuẩn bị đã được tạo, em sửa trong bài đó nhé")
    status = body.status or it.status
    if body.payload is not None:
        try:
            numeric = it.kind == "quiz" and body.payload.get("item_type") == "NUMERIC"
            model: Any = quizgen.AiNumeric if numeric else quizgen.AiQuestion if it.kind == "quiz" else quizgen.AiCard
            draft = model.model_validate(body.payload)
            if numeric and not quizgen.numeric_math_ok(draft):
                raise ValueError("answer does not follow from the operands")
            if numeric:
                draft.answer = quizgen.numeric_value(draft)  # the key is always the server's own result
            it.payload = draft.model_dump(mode="json")
        except ValueError as e:
            raise ApiError(422, "PAYLOAD_INVALID", "Nội dung chưa hợp lệ: cần đủ 4 phương án, 3 gợi ý và đoạn trích nguồn (câu trả lời số: đáp án phải khớp phép tính)") from e
        status = body.status or "draft"
    it.status = status
    it.needs_confirmation = status != "approved"  # the model's answer counts as confirmed only when the teacher approves it
    await db.commit()
    return _ai_out(it)


async def regenerate_ai(db: AsyncSession, user: CurrentUser, plan_id: UUID, body: PlanAiRegenerate) -> PlanOut:
    """Approved items stay, the rest is redrafted in the background."""
    p = await _own(db, user, plan_id)
    if not get_settings().quiz_gen_enabled:
        raise ApiError(409, "QUIZ_GEN_OFF", "Tính năng AI soạn câu hỏi đang tắt")
    total = body.mcq + body.numeric
    if total > get_settings().quiz_gen_per_lesson:
        raise ApiError(422, "QUIZ_COUNT", f"Tổng số câu không quá {get_settings().quiz_gen_per_lesson}")
    if p.ai_state in ("queued", "running"):
        raise ApiError(409, "AI_BUSY", "AI đang soạn câu hỏi cho giáo án này")
    if await _lesson_of(db, p) is not None:
        raise ApiError(409, "LESSON_EXISTS", "Bài chuẩn bị đã được tạo, không soạn lại được")
    p.ai_state = "queued"
    await db.commit()
    quizgen.start(p.id, quizgen.QuizSpec(body.mcq, body.numeric, body.level))
    return await _out(db, p)


def _anchor_for(quote: str, by: dict[UUID, m.SourceAnchor]) -> m.SourceAnchor | None:
    """The plan paragraph a drafted item quotes (provenance): the one holding most of the quote's words."""
    q = set(rules.norm(quote).split())
    best = max(by.values(), key=lambda a: len(q & set(rules.norm(a.excerpt).split())), default=None)
    return best if best is not None and q & set(rules.norm(best.excerpt).split()) else None


def _number_sources(text: str, main: m.SourceAnchor, by: dict[UUID, m.SourceAnchor]) -> tuple[m.SourceAnchor, ...]:
    """Other plan paragraphs that hold a number used in `text` (a distractor may take its figure from elsewhere in the plan): VAL-03
    checks every number of a block against the paragraphs it cites."""
    need = set(parse_numbers(text)) - set(parse_numbers(main.excerpt))
    out: list[m.SourceAnchor] = []
    for a in by.values():
        have = need & set(parse_numbers(a.excerpt))
        if have:
            out.append(a)
            need -= have
    return tuple(out)


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

    lesson = m.Lesson(author_id=user.id, grade=p.grade if p.grade in (10, 11) else 10, title=default_title(p.title),
                      goal="Bài chuẩn bị trước giờ học, dựng từ giáo án.", teach_date=p.taught_from, lesson_plan_id=p.id)
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
    cat = set(await db.scalars(select(m.SubjectCompetency.code).where(m.SubjectCompetency.subject == p.subject)))
    objs = (await db.scalars(select(m.Objective).where(m.Objective.lesson_plan_id == p.id).order_by(m.Objective.id))).all()
    meta: dict[str, dict[str, Any]] = {}

    def tag(key: str, code: str | None) -> None:
        """Competency of a block: the teacher's choice (MCQ) or the activity default; the objective with the same code."""
        if code is None or code not in cat:
            return
        obj = next((o.id for o in objs if o.competency_code == code), None)
        meta[key] = {"competency_code": code, "objective_id": obj}

    def add(key: str, kind: str, payload: dict[str, Any], anchor: m.SourceAnchor, *, parent: str | None = None,
            tr: str = "ORIGINAL", factual: bool = False, code: str | None = None, more: tuple[m.SourceAnchor, ...] = ()) -> None:
        tag(key, code)
        blocks.append(DraftBlock(key=key, kind=kind, parentKey=parent, payload=payload, transformation=tr,
                                 anchorAliases=[alias[a.id] for a in (anchor, *more)], isFactual=factual))

    opening = anchors_of("mo_dau")
    trig = _first(opening, lambda a: a.excerpt.rstrip().endswith("?")) or _first(opening, lambda a: len(a.excerpt) > 20)
    if trig:
        add("open", "instruction", {"text": trig.excerpt}, trig, code=ACTIVITY_COMPETENCY["mo_dau"])
    boxes = [a for a in anchors_of("hinh_thanh") if a.locator.get("type") == "knowledge_box"][:2]
    for i, b in enumerate(boxes, 1):
        add(f"read{i}", "paragraph", {"text": b.excerpt}, b, factual=True, code=ACTIVITY_COMPETENCY["hinh_thanh"])
    if boxes:
        add("fc", "card_front", {"text": "Em nhớ gì về nội dung này?"}, boxes[0], tr="SYNTHESISED", code=ACTIVITY_COMPETENCY["hinh_thanh"])
        add("fcb", "card_back", {"text": boxes[0].excerpt}, boxes[0], parent="fc", code=ACTIVITY_COMPETENCY["hinh_thanh"])
    ok = [q for q in mcqs if not q.needs_confirmation and q.correct_option]
    chosen = ok[:MAX_PRACTICE]
    for n, q in enumerate(chosen, 1):
        stem = by[q.stem_anchor_id]
        opts = [by[a] for a in q.option_anchor_ids]
        cc = q.competency_code
        add(f"q{n}", "worksheet_item", {"stem": stem.excerpt, "itemType": "MCQ", "skill": "EXPLAIN"}, stem, code=cc)
        for i, o in enumerate(opts):
            add(f"q{n}{chr(97 + i)}", "option", {"label": chr(65 + i), "text": o.excerpt}, o, parent=f"q{n}", code=cc)
        right = opts[ord(q.correct_option or "A") - 65]
        add(f"q{n}k", "answer_key", {"correct": q.correct_option}, right, parent=f"q{n}", code=cc)  # the pipeline never lets a generator claim TEACHER_AUTHORED; the confirmed option is quoted
        add(f"q{n}e", "explanation", {"text": f"Đáp án đúng là {q.correct_option}. {right.excerpt}"}, right, parent=f"q{n}", tr="SYNTHESISED", code=cc)
    ai = (await db.scalars(select(m.PlanAiItem).where(m.PlanAiItem.lesson_plan_id == p.id, m.PlanAiItem.status == "approved")
                           .order_by(m.PlanAiItem.kind, m.PlanAiItem.position))).all()
    ai_q = 0
    for it in ai:  # only what the teacher approved; the blocks still go through the normal review and publish gate
        src = _anchor_for(it.source_quote, by)
        if src is None:
            continue
        d = quizgen.clean_payload(it.kind, it.payload)  # sentence ids from older drafts never reach students
        if it.kind == "review":
            card = {"title": d["title"], "points": d["points"], "example": d["example"],
                    "check": {"statement": d["check"]["statement"], "answerTrue": d["check"]["answer_true"], "explanation": d["check"]["explanation"]}}
            add(f"rv{len(blocks)}", "review_card", card, src, tr="AI_PROPOSED",
                more=_number_sources(" ".join([d["title"], *d["points"], d["example"], d["check"]["statement"]]), src, by))
            continue
        ai_q += 1
        k = f"aq{ai_q}"
        level = {"level": d["level"]} if d.get("level") else {}
        if d.get("item_type") == "NUMERIC":  # part III: the key is the server's own result, with the derivation VAL-03 recomputes
            more = _number_sources(d["stem"], src, by)
            deriv = {"op": d["op"], "operands": d["operands"]}
            add(k, "worksheet_item", {"stem": d["stem"], "itemType": "NUMERIC", "skill": d["skill_tag"], "hints": d["hints"],
                                      "sourceQuote": it.source_quote[:500], **level}, src, tr="AI_PROPOSED", more=more)
            add(f"{k}k", "answer_key", {"value": d["answer"], "unit": d["unit"], "tolerance": 0.05, "derivation": deriv}, src,
                parent=k, tr="AI_PROPOSED", more=more)
            add(f"{k}e", "explanation", {"text": d["explanation"], "derivation": deriv}, src, parent=k, tr="AI_PROPOSED", more=more)
            continue
        add(k, "worksheet_item", {"stem": d["stem"], "itemType": "MCQ", "skill": d["skill_tag"], "hints": d["hints"],
                          "sourceQuote": it.source_quote[:500], **level}, src, tr="AI_PROPOSED",
            more=_number_sources(d["stem"], src, by))
        for i, o in enumerate(d["options"]):
            add(f"{k}{chr(97 + i)}", "option", {"label": chr(65 + i), "text": o}, src, parent=k, tr="AI_PROPOSED", more=_number_sources(o, src, by))
        add(f"{k}k", "answer_key", {"correct": chr(65 + d["correct_index"])}, src, parent=k, tr="AI_PROPOSED")
        add(f"{k}e", "explanation", {"text": d["explanation"]}, src, parent=k, tr="AI_PROPOSED", more=_number_sources(d["explanation"], src, by))
    apply = _first(anchors_of("van_dung"), lambda a: len(a.excerpt) > 20)
    if apply:
        add("apply", "instruction", {"text": apply.excerpt}, apply, code=ACTIVITY_COMPETENCY["van_dung"])
    n = await _persist(db, rev, Draft(blocks=blocks), views, alias_id, "plan-5512/1", meta)
    await db.commit()
    await validate_revision(db, rev.id)
    return PlanLessonOut(lesson_id=lesson.id, blocks=n, practice_items=len(chosen) + ai_q,
                         skipped_unconfirmed=len(mcqs) - len(ok), left_for_after_class=max(0, len(ok) - MAX_PRACTICE))
