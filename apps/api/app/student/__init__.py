"""Student side (PR-08): whitelist DTOs built from the published snapshot only. Never touches provenance, review,
validation or the live (editable) blocks."""

import csv
import io
from datetime import UTC, datetime
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.blocks import NOT_FOUND
from app.config import get_settings
from app.db import models as m
from app.errors import ApiError
from app.habit.activity import bump
from app.schemas import (
    AnswerIn,
    AttemptRequest,
    AttemptResult,
    ProgressItem,
    ProgressOut,
    StudentAssignmentList,
    StudentAssignmentOut,
    StudentAssignmentSummary,
    StudentContentBlock,
    StudentItem,
    StudentOption,
)

_CONTENT = {"heading", "paragraph", "data_fact", "instruction", "card_front"}  # card_back is the answer: never listed


def _now() -> datetime:
    return datetime.now(UTC)


async def _load(db: AsyncSession, user: CurrentUser, assignment_id: UUID) -> tuple[m.Assignment, m.PublishedVersion, str]:
    """Assignment visible to this student: member of the class and already open. Anything else is a 404."""
    row = (await db.execute(
        select(m.Assignment, m.PublishedVersion, m.Class.code)
        .join(m.PublishedVersion, m.PublishedVersion.id == m.Assignment.published_version_id)
        .join(m.Class, m.Class.id == m.Assignment.class_id)
        .join(m.ClassMember, (m.ClassMember.class_id == m.Class.id) & (m.ClassMember.user_id == user.id)
              & (m.ClassMember.role_in_class == "STUDENT"))
        .where(m.Assignment.id == assignment_id))).first()
    if row is None or row[0].open_at > _now():
        raise NOT_FOUND
    if row[1].state == "WITHDRAWN":
        raise ApiError(410, "WITHDRAWN", "Bài này đã được giáo viên thu hồi")
    return row[0], row[1], row[2]


def _items(snap: dict[str, Any]) -> list[dict[str, Any]]:
    return [b for b in snap["blocks"] if b["kind"] == "worksheet_item"]


def _children(snap: dict[str, Any], item_id: str, kind: str) -> list[dict[str, Any]]:
    return [b for b in snap["blocks"] if b["parentId"] == item_id and b["kind"] == kind]


def _grade(item_type: str, key: dict[str, Any] | None, ans: AnswerIn) -> bool | None:
    if item_type == "SHORT" or key is None:
        return None  # rubric items are not auto-graded
    if item_type == "MCQ":
        return ans.choice is not None and ans.choice == key.get("correct")
    if ans.value is None or key.get("value") is None:
        return False
    return abs(ans.value - float(key["value"])) <= float(key.get("tolerance") or 0) + 1e-9


def _result(snap: dict[str, Any], item_id: str, is_correct: bool | None) -> AttemptResult:
    exp = next(iter(_children(snap, item_id, "explanation")), None)
    return AttemptResult(item_id=UUID(item_id), is_correct=is_correct, explanation=exp["payload"]["text"] if exp else None)


async def _attempts(db: AsyncSession, assignment_id: UUID, student_id: UUID) -> dict[UUID, m.StudentAttempt]:
    rows = (await db.execute(select(m.StudentAttempt).where(
        m.StudentAttempt.assignment_id == assignment_id, m.StudentAttempt.student_id == student_id))).scalars().all()
    return {a.item_block_id: a for a in rows}


async def get_assignment(db: AsyncSession, user: CurrentUser, assignment_id: UUID) -> StudentAssignmentOut:
    a, pv, _ = await _load(db, user, assignment_id)
    snap = pv.snapshot
    done = await _attempts(db, a.id, user.id)
    blocks = [StudentContentBlock(id=UUID(b["id"]), kind=b["kind"], position=b["position"], payload=b["payload"])
              for b in snap["blocks"] if b["kind"] in _CONTENT]
    items: list[StudentItem] = []
    for it in _items(snap):
        p = it["payload"]
        opts = sorted(_children(snap, it["id"], "option"), key=lambda o: o["payload"]["label"])
        att = done.get(UUID(it["id"]))
        items.append(StudentItem(
            id=UUID(it["id"]), position=it["position"], item_type=p["itemType"], skill=p["skill"], stem=p["stem"],
            options=[StudentOption(label=o["payload"]["label"], text=o["payload"]["text"]) for o in opts],
            result=_result(snap, it["id"], att.is_correct) if att else None))
    return StudentAssignmentOut(id=a.id, title=snap["title"], open_at=a.open_at, due_at=a.due_at, blocks=blocks, items=items)


async def list_assignments(db: AsyncSession, user: CurrentUser) -> StudentAssignmentList:
    rows = (await db.execute(
        select(m.Assignment, m.PublishedVersion, m.Class.code, m.Class.name)
        .join(m.PublishedVersion, m.PublishedVersion.id == m.Assignment.published_version_id)
        .join(m.Class, m.Class.id == m.Assignment.class_id)
        .join(m.ClassMember, (m.ClassMember.class_id == m.Class.id) & (m.ClassMember.user_id == user.id)
              & (m.ClassMember.role_in_class == "STUDENT"))
        .where(m.Assignment.open_at <= func.now(), m.PublishedVersion.state == "ACTIVE")
        .order_by(m.Assignment.due_at))).all()
    now = _now()
    out: list[StudentAssignmentSummary] = []
    for a, pv, code, cname in rows:
        n, answered = len(_items(pv.snapshot)), len(await _attempts(db, a.id, user.id))
        status = ("DONE" if n and answered >= n else "CLOSED" if now > a.due_at
                  else "IN_PROGRESS" if answered else "NOT_STARTED")
        out.append(StudentAssignmentSummary(
            id=a.id, title=pv.snapshot["title"], class_code=code, class_name=cname or code, open_at=a.open_at,
            due_at=a.due_at, status=status, answered_count=answered, item_count=n))
    return StudentAssignmentList(items=out)


async def submit_attempt(db: AsyncSession, user: CurrentUser, assignment_id: UUID, body: AttemptRequest) -> AttemptResult:
    a, pv, _ = await _load(db, user, assignment_id)
    snap = pv.snapshot
    item = next((i for i in _items(snap) if i["id"] == str(body.item_id)), None)
    if item is None:
        raise NOT_FOUND  # not an item of this assignment's snapshot
    existing = (await _attempts(db, a.id, user.id)).get(body.item_id)
    if existing is not None:
        if existing.request_id == body.request_id:  # retry of the same submit: idempotent
            return _result(snap, item["id"], existing.is_correct)
        raise ApiError(409, "ALREADY_ANSWERED", "Bạn đã trả lời câu này rồi")
    if _now() > a.due_at:
        raise ApiError(409, "PAST_DUE", "Bài đã quá hạn nộp. Em vẫn xem lại được bài và lời giải")
    key = next(iter(_children(snap, item["id"], "answer_key")), None)
    ok = _grade(item["payload"]["itemType"], key["payload"] if key else None, body.answer)
    got = await db.scalar(pg_insert(m.StudentAttempt).values(
        assignment_id=a.id, student_id=user.id, item_block_id=body.item_id,
        answer=body.answer.model_dump(exclude_none=True), is_correct=ok, request_id=body.request_id)
        .on_conflict_do_nothing().returning(m.StudentAttempt.id))
    if got is None:  # lost a race (same item) or the requestId is taken: nothing was written
        again = (await _attempts(db, a.id, user.id)).get(body.item_id)
        if again is not None and again.request_id == body.request_id:
            return _result(snap, item["id"], again.is_correct)
        raise ApiError(409, "ALREADY_ANSWERED", "Bạn đã trả lời câu này rồi")
    if get_settings().chat_enabled:
        await bump(db, user.id, items=1)
    await db.commit()
    return _result(snap, item["id"], ok)


async def _teacher_assignment(db: AsyncSession, user: CurrentUser, class_id: UUID,
                              assignment_id: UUID) -> tuple[m.Assignment, m.PublishedVersion]:
    """The assignment, only for a TEACHER of that class; anything else is 404."""
    row = (await db.execute(
        select(m.Assignment, m.PublishedVersion)
        .join(m.PublishedVersion, m.PublishedVersion.id == m.Assignment.published_version_id)
        .join(m.ClassMember, (m.ClassMember.class_id == m.Assignment.class_id) & (m.ClassMember.user_id == user.id)
              & (m.ClassMember.role_in_class == "TEACHER"))
        .where(m.Assignment.id == assignment_id, m.Assignment.class_id == class_id))).first()
    if row is None:
        raise NOT_FOUND
    return row[0], row[1]


async def _class_students(db: AsyncSession, class_id: UUID) -> list[tuple[UUID, str]]:
    """(id, label) of every student of the class: never a name. Account students by login code (it needs a password).
    Guests get "Khách 001", "Khách 002"... in the order they joined: never the survey code, which alone logs a guest
    back in (POST /auth/guest/resume), nor the display name, which contains it."""
    rows = (await db.execute(
        select(m.AppUser.id, m.AppUser.is_guest, m.AppUser.login_code)
        .join(m.ClassMember, m.ClassMember.user_id == m.AppUser.id)
        .where(m.ClassMember.class_id == class_id, m.ClassMember.role_in_class == "STUDENT")
        # a guest's login_code IS its survey code: guests are ordered by when they joined, never by code
        .order_by(m.AppUser.is_guest, case((m.AppUser.is_guest, None), else_=m.AppUser.login_code),
                  m.AppUser.created_at, m.AppUser.id))).all()
    out: list[tuple[UUID, str]] = []
    guests = 0
    for sid, is_guest, code in rows:
        if is_guest:
            guests += 1
            out.append((sid, f"Khách {guests:03d}"))
        else:
            out.append((sid, code or ""))
    return out


async def progress(db: AsyncSession, user: CurrentUser, class_id: UUID, assignment_id: UUID) -> ProgressOut:
    a, pv = await _teacher_assignment(db, user, class_id, assignment_id)
    students = await db.scalar(select(func.count()).select_from(m.ClassMember).where(
        m.ClassMember.class_id == class_id, m.ClassMember.role_in_class == "STUDENT")) or 0
    stats = {r[0]: (r[1], r[2], r[3]) for r in (await db.execute(
        select(m.StudentAttempt.item_block_id, func.count(), func.count(m.StudentAttempt.is_correct),
               func.count().filter(m.StudentAttempt.is_correct.is_(True)))
        .where(m.StudentAttempt.assignment_id == a.id).group_by(m.StudentAttempt.item_block_id))).all()}
    item_ids = [UUID(it["id"]) for it in _items(pv.snapshot)]
    per_student = (await db.execute(
        select(func.count(m.StudentAttempt.item_block_id.distinct()))
        .join(m.ClassMember, (m.ClassMember.user_id == m.StudentAttempt.student_id)
              & (m.ClassMember.class_id == class_id) & (m.ClassMember.role_in_class == "STUDENT"))
        .where(m.StudentAttempt.assignment_id == a.id, m.StudentAttempt.item_block_id.in_(item_ids))
        .group_by(m.StudentAttempt.student_id))).scalars().all()
    completed = sum(1 for n in per_student if item_ids and n >= len(item_ids))
    items = []
    for it in _items(pv.snapshot):
        n, graded, right = stats.get(UUID(it["id"]), (0, 0, 0))
        items.append(ProgressItem(item_block_id=UUID(it["id"]), stem=it["payload"]["stem"], answered_count=n,
                                  first_attempt_correct_rate=right / graded if graded else None))
    return ProgressOut(assignment_id=a.id, student_count=students, completed_count=completed,
                       in_progress_count=len(per_student) - completed, items=items)


VN_TZ = ZoneInfo("Asia/Ho_Chi_Minh")


def _safe(cell: str) -> str:
    return "'" + cell if cell[:1] in ("=", "+", "-", "@", "\t", "\r") else cell  # CSV formula injection


def _answer_text(answer: dict[str, Any]) -> str:
    if answer.get("choice") is not None:
        return str(answer["choice"])
    if answer.get("value") is not None:
        v = float(answer["value"])
        return (str(int(v)) if v.is_integer() else str(v)).replace(".", ",")  # Vietnamese decimal comma
    return _safe(" ".join(str(answer.get("text") or "").split()))


async def export_results_csv(db: AsyncSession, user: CurrentUser, class_id: UUID, assignment_id: UUID) -> tuple[str, str]:
    """(file name, CSV) like a Google Form response sheet: one row per student of the class (login code, or
    "Khách 001"... for guests: never a name nor a survey code; never ranked), one answer and one Đúng/Sai
    column per item. Starts with a BOM so Excel reads Vietnamese."""
    a, pv = await _teacher_assignment(db, user, class_id, assignment_id)
    items = _items(pv.snapshot)
    students = await _class_students(db, class_id)
    attempts: dict[UUID, dict[UUID, m.StudentAttempt]] = {}
    for row in (await db.execute(select(m.StudentAttempt).where(m.StudentAttempt.assignment_id == a.id))).scalars():
        attempts.setdefault(row.student_id, {})[row.item_block_id] = row
    out = io.StringIO()
    out.write("\ufeff")
    w = csv.writer(out, lineterminator="\r\n")
    head = ["Mã học sinh", "Trạng thái", "Số câu đã làm", "Số câu đúng", "Số câu chấm tự động", "Lần trả lời cuối"]
    for n in range(1, len(items) + 1):
        head += [f"Câu {n} - Trả lời", f"Câu {n} - Kết quả"]
    w.writerow(head)
    for sid, code in students:
        done = attempts.get(sid, {})
        row_items: list[str] = []
        answered = right = graded = 0
        last: datetime | None = None
        for it in items:
            att = done.get(UUID(it["id"]))
            if att is None:
                row_items += ["", ""]
                continue
            answered += 1
            last = att.created_at if last is None or att.created_at > last else last
            if att.is_correct is not None:
                graded += 1
                right += int(att.is_correct)
            result = "Không chấm tự động" if att.is_correct is None else "Đúng" if att.is_correct else "Sai"
            row_items += [_answer_text(att.answer), result]
        status = "Đã xong" if items and answered >= len(items) else "Đang làm" if answered else "Chưa làm"
        w.writerow([_safe(code), status, answered, right, graded,
                    last.astimezone(VN_TZ).strftime("%d/%m/%Y %H:%M") if last else "", *row_items])
    return f"ket-qua-{a.id.hex[:8]}.csv", out.getvalue()
