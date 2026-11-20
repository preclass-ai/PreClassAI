"""Habit (ADR-0012): step-by-step hints, a scoped chat and study habits for students.

Grounding: only the published snapshot of an assignment the student belongs to (`student._load`). The answer key and the
explanation are used for exactly two things: the leak guard, and `explain` after the student's own attempt.
Threats and tests: docs/security/THREAT-MODEL-habit.md.
"""

from collections import OrderedDict
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import student
from app.auth import CurrentUser
from app.blocks import NOT_FOUND
from app.config import get_settings
from app.db import models as m
from app.errors import ApiError
from app.habit import llm, rules
from app.habit.activity import bump, day_start_utc, today
from app.schemas import ChatReply, ChatRequest, HabitBadge, HabitItem, HabitOut, SourceRef

HINTS_MAX = 3
_CACHE: OrderedDict[tuple[Any, ...], str] = OrderedDict()  # (day, item, level, normalised message) → reply; ≤200 entries
BADGES = {"TU_LUC": "Tự lực", "KIEN_TRI": "Kiên trì", "THAM_HIEM": "Thám hiểm"}


def _enabled() -> None:
    if not get_settings().chat_enabled:
        raise NOT_FOUND


def _reply(text: str, level: int, refs: list[tuple[str, str, str]], reason: str | None) -> ChatReply:
    return ChatReply(reply=text, hint_level=level, blocked_reason=reason,
                     source_refs=[SourceRef(block_id=UUID(i), label=lab, excerpt=t[:400]) for i, lab, t in refs])


async def _session(db: AsyncSession, assignment_id: UUID, student_id: UUID, item_id: UUID) -> UUID:
    ins = pg_insert(m.ChatSession).values(assignment_id=assignment_id, student_id=student_id, item_block_id=item_id)
    await db.execute(ins.on_conflict_do_nothing())
    return (await db.execute(select(m.ChatSession.id).where(
        m.ChatSession.assignment_id == assignment_id, m.ChatSession.student_id == student_id,
        m.ChatSession.item_block_id == item_id))).scalar_one()


async def _llm_reply(db: AsyncSession, v: rules.ItemView, level: int, msg: str, base: str, excerpt: str, sess: UUID,
                     key: tuple[Any, ...]) -> tuple[str | None, str | None, int, int]:
    """(reply, fallback_reason, tokens_in, tokens_out). Any problem → (None, reason, …) and the caller keeps the rule reply."""
    cfg = get_settings()
    client = llm.get_chat_llm()
    if client is None:
        return None, "LLM_ERROR", 0, 0
    if key in _CACHE:
        return _CACHE[key], None, 0, 0
    used = await db.scalar(select(func.coalesce(func.sum(m.ChatMessage.tokens_in + m.ChatMessage.tokens_out), 0)).where(
        m.ChatMessage.created_at >= day_start_utc())) or 0
    if used >= cfg.chat_daily_token_budget:
        return None, "LLM_BUDGET", 0, 0
    hist = (await db.execute(select(m.ChatMessage.role, m.ChatMessage.text).where(m.ChatMessage.session_id == sess)
                             .order_by(m.ChatMessage.created_at.desc()).limit(4))).all()
    history = [f"{r}: {t}" for r, t in reversed(hist)]
    try:
        out, tin, tout = await client.complete(llm.SYSTEM, llm.build_user(v, level, msg, history, excerpt),
                                               cfg.chat_max_output_tokens)
    except Exception:  # noqa: BLE001 timeout, HTTP error, bad payload: all mean "use the rule reply"
        return None, "LLM_ERROR", 0, 0
    out = out.strip()[:600]
    bad = llm.postcheck(out, v)
    if bad:
        return None, bad, tin, tout
    _CACHE[key] = out
    if len(_CACHE) > 200:
        _CACHE.popitem(last=False)
    return out, None, tin, tout


async def chat(db: AsyncSession, user: CurrentUser, assignment_id: UUID, body: ChatRequest) -> ChatReply:
    _enabled()
    cfg = get_settings()
    a, pv, _ = await student._load(db, user, assignment_id)  # noqa: SLF001
    item = next((i for i in student._items(pv.snapshot) if i["id"] == str(body.item_id)), None)  # noqa: SLF001
    if item is None:
        raise NOT_FOUND
    v = rules.build_view(pv.snapshot, item)
    answered = body.item_id in await student._attempts(db, a.id, user.id)  # noqa: SLF001
    sess = await _session(db, a.id, user.id, body.item_id)

    prev = (await db.execute(select(m.ChatMessage).where(
        m.ChatMessage.session_id == sess, m.ChatMessage.request_id == body.request_id,
        m.ChatMessage.role == "assistant"))).scalar_one_or_none()
    if prev is not None:  # retry of the same request: stored reply, no new quota
        return _reply(prev.text, prev.hint_level or 0, [], prev.blocked_reason if prev.blocked_reason in rules.REFUSAL else None)

    if body.action == "explain" and not answered:
        raise ApiError(409, "NOT_ANSWERED", "Em hãy trả lời câu này trước, rồi Habit sẽ giải thích nhé")
    if body.action == "hint" and answered:
        raise ApiError(409, "ALREADY_ANSWERED", "Câu này đã nộp rồi, em bấm “Habit giải thích” để xem lời giải nhé")
    if body.action == "ask" and not (body.message or "").strip():
        raise ApiError(422, "MESSAGE_REQUIRED", "Em hãy nhập câu hỏi")
    per_item = await db.scalar(select(func.count()).where(
        m.ChatMessage.session_id == sess, m.ChatMessage.role == "assistant")) or 0
    per_day = await db.scalar(select(func.count()).select_from(m.ChatMessage).join(
        m.ChatSession, m.ChatSession.id == m.ChatMessage.session_id).where(
        m.ChatSession.student_id == user.id, m.ChatMessage.role == "assistant",
        m.ChatMessage.created_at >= day_start_utc())) or 0
    if per_item >= cfg.chat_max_per_item or per_day >= cfg.chat_max_per_day_per_student:
        raise ApiError(429, "CHAT_LIMIT", "Hôm nay em hỏi nhiều rồi, thử tự làm nhé!")

    msg = rules.redact((body.message or "").strip()) if body.action == "ask" else ""
    used = await db.scalar(select(func.count()).where(
        m.ChatMessage.session_id == sess, m.ChatMessage.action == "hint", m.ChatMessage.role == "assistant")) or 0
    text, level, refs, reason = rules.decide(v, body.action, msg, used)
    mode, tin, tout = "rule", 0, 0
    if body.action != "explain":
        if cfg.chat_mode == "llm" and reason is None:
            excerpt = " ".join(t for _, _, t in (refs or v.blocks))
            key = (today(), pv.id, body.item_id, level, rules.norm(msg))
            out, fb, tin, tout = await _llm_reply(db, v, level, msg, text, excerpt, sess, key)
            if out is not None:
                text, mode = out, "llm"
            else:
                reason = fb

    try:
        async with db.begin_nested():
            db.add(m.ChatMessage(session_id=sess, role="user", action=body.action, text=msg or "(gợi ý)", mode="rule"))
            db.add(m.ChatMessage(session_id=sess, role="assistant", action=body.action, text=text,
                                 hint_level=level if body.action == "hint" else None, mode=mode, blocked_reason=reason,
                                 tokens_in=tin, tokens_out=tout, request_id=body.request_id))
    except IntegrityError:  # double click: the other request won
        again = (await db.execute(select(m.ChatMessage).where(
            m.ChatMessage.session_id == sess, m.ChatMessage.request_id == body.request_id,
            m.ChatMessage.role == "assistant"))).scalar_one()
        return _reply(again.text, again.hint_level or 0, [], None)
    if body.action == "hint":
        await bump(db, user.id, hints=1)
    await db.commit()
    return _reply(text, level, refs, reason if reason in rules.REFUSAL else None)


async def habit(db: AsyncSession, user: CurrentUser, assignment_id: UUID) -> HabitOut:
    _enabled()
    a, pv, _ = await student._load(db, user, assignment_id)  # noqa: SLF001
    cfg = get_settings()
    rows = (await db.execute(select(m.StudyActivity.day, m.StudyActivity.items_answered).where(
        m.StudyActivity.student_id == user.id).order_by(m.StudyActivity.day.desc()).limit(400))).all()
    done = {d: n for d, n in rows}
    days = {d for d, n in done.items() if n >= 1}
    d, streak = today(), 0
    if d not in days:
        d = d.fromordinal(d.toordinal() - 1)  # today has no answer yet: the streak is still alive from yesterday
    while d in days:
        streak, d = streak + 1, d.fromordinal(d.toordinal() - 1)
    hints = {r[0]: (r[1], r[2]) for r in (await db.execute(
        select(m.ChatSession.item_block_id, func.count(), func.max(m.ChatMessage.hint_level))
        .join(m.ChatSession, m.ChatSession.id == m.ChatMessage.session_id)
        .where(m.ChatSession.assignment_id == a.id, m.ChatSession.student_id == user.id,
               m.ChatMessage.role == "assistant", m.ChatMessage.action == "hint")
        .group_by(m.ChatSession.item_block_id))).all()}
    right = (await db.execute(select(m.StudentAttempt.item_block_id).where(
        m.StudentAttempt.assignment_id == a.id, m.StudentAttempt.student_id == user.id,
        m.StudentAttempt.is_correct.is_(True)))).scalars().all()
    earned = []
    if any(i not in hints for i in right):
        earned.append("TU_LUC")
    if streak >= 3:
        earned.append("KIEN_TRI")
    if any((hints[i][1] or 0) >= 2 for i in right if i in hints):
        earned.append("THAM_HIEM")
    return HabitOut(
        streak=streak, today_goal=cfg.habit_daily_goal, today_done=done.get(today(), 0),
        badges=[HabitBadge(code=c, label=BADGES[c]) for c in earned],
        hints_available=[HabitItem(item_id=UUID(i["id"]), hints_used=min((hints.get(UUID(i["id"])) or (0, 0))[0], HINTS_MAX),
                                   hints_max=HINTS_MAX) for i in student._items(pv.snapshot)])  # noqa: SLF001


async def chat_stats(db: AsyncSession) -> dict[str, Any]:
    """Counters for /admin/survey/stats. No message text."""
    rows = (await db.execute(select(m.ChatMessage.blocked_reason, m.ChatMessage.mode, func.count(),
                                    func.coalesce(func.sum(m.ChatMessage.tokens_in), 0),
                                    func.coalesce(func.sum(m.ChatMessage.tokens_out), 0))
                             .where(m.ChatMessage.role == "assistant")
                             .group_by(m.ChatMessage.blocked_reason, m.ChatMessage.mode))).all()
    total = sum(r[2] for r in rows)
    fb = sum(r[2] for r in rows if (r[0] or "").startswith("LLM_"))
    llm_try = sum(r[2] for r in rows if r[1] == "llm") + fb
    blocked: dict[str, int] = {}
    for reason, _, n, _, _ in rows:
        if reason:
            blocked[reason] = blocked.get(reason, 0) + n
    return {"chat_total": total, "chat_fallback_rate": fb / llm_try if llm_try else 0.0, "chat_blocked": blocked,
            "chat_tokens_in": sum(int(r[3]) for r in rows), "chat_tokens_out": sum(int(r[4]) for r in rows)}
