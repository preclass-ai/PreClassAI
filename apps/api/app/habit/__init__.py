# ruff: noqa: E501
"""Habit (ADR-0012): step-by-step hints, a scoped chat and study habits for students.

Grounding: only the published snapshot of an assignment the student belongs to (`student._load`). The answer key and the
explanation are used for exactly two things: the leak guard, and `explain` after the student's own attempt.
Threats and tests: docs/security/THREAT-MODEL-habit.md.
"""

import logging
from collections import OrderedDict
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import personalization, student
from app.auth import CurrentUser
from app.blocks import NOT_FOUND
from app.config import get_settings
from app.db import models as m
from app.errors import ApiError
from app.habit import llm, rules
from app.habit.activity import bump, day_start_utc, today
from app.schemas import ChatReply, ChatRequest, HabitBadge, HabitItem, HabitOut, QuickAction, SourceRef
from app.student import review

log = logging.getLogger(__name__)
GUIDE = " Em đọc lại đoạn nguồn trong bài rồi thử làm nhé."
REVIEW_ASK = ("chua hoc", "chua on", "bat dau tu dau", "nen on gi", "on gi truoc", "chua biet gi")  # "I have not studied this"
_CACHE: OrderedDict[tuple[Any, ...], str] = OrderedDict()  # (day, item, level, normalised message) → reply; ≤200 entries
BADGES = {"TU_LUC": "Tự lực", "KIEN_TRI": "Kiên trì", "THAM_HIEM": "Thám hiểm"}


def _enabled() -> None:
    if not get_settings().chat_enabled:
        raise NOT_FOUND


EXTRA_SEP = "\n\n[EXTRA]\n\n"  # the stored text holds both parts; the API returns them separately


def _reply(text: str, level: int, refs: list[tuple[str, str, str]], reason: str | None, mode: str = "rule", hints_used: int | None = None,
           open_review: str | None = None) -> ChatReply:
    main, _, extra = text.partition(EXTRA_SEP)
    offer = (reason in rules.REFUSAL and reason != "UNSAFE") or text in rules.SMALL_REPLY["INTRO"]  # intro: show the buttons
    sugg = [QuickAction(id=k, label=lab) for k, lab in rules.SUGGESTIONS] if offer else []
    return ChatReply(
        reply=main, hint_level=level, blocked_reason=reason if reason in rules.REFUSAL else None, extra=extra or None,
        suggestions=sugg, source_refs=[SourceRef(block_id=UUID(i), label=lab, excerpt=t[:400]) for i, lab, t in refs],
        source="llm" if mode == "llm" else "guard" if reason in rules.REFUSAL else "rule", hints_used=hints_used,
        open_review=UUID(open_review) if open_review else None)


async def _session(db: AsyncSession, assignment_id: UUID, student_id: UUID, item_id: UUID) -> UUID:
    ins = pg_insert(m.ChatSession).values(assignment_id=assignment_id, student_id=student_id, item_block_id=item_id)
    await db.execute(ins.on_conflict_do_nothing())
    return (await db.execute(select(m.ChatSession.id).where(
        m.ChatSession.assignment_id == assignment_id, m.ChatSession.student_id == student_id,
        m.ChatSession.item_block_id == item_id))).scalar_one()


async def _llm_reply(db: AsyncSession, v: rules.ItemView, level: int, msg: str, base: str, excerpt: str, sess: UUID,
                     key: tuple[Any, ...]) -> tuple[str | None, str | None, int, int, str | None]:
    """(reply, fallback_reason, tokens_in, tokens_out, model). A problem gives (None, reason, ...): the rule reply stays."""
    cfg = get_settings()
    client = llm.get_chat_llm()
    if client is None:
        return None, "LLM_ERROR", 0, 0, None
    if key in _CACHE:
        return _CACHE[key], None, 0, 0, "cache"
    used = await db.scalar(select(func.coalesce(func.sum(m.ChatMessage.tokens_in + m.ChatMessage.tokens_out), 0)).where(
        m.ChatMessage.created_at >= day_start_utc())) or 0
    if used >= cfg.chat_daily_token_budget:
        return None, "LLM_BUDGET", 0, 0, None
    hist = (await db.execute(select(m.ChatMessage.role, m.ChatMessage.text).where(m.ChatMessage.session_id == sess)
                             .order_by(m.ChatMessage.created_at.desc()).limit(4))).all()
    history = [f"{r}: {t}" for r, t in reversed(hist)]
    try:
        raw, tin, tout = await client.complete(llm.SYSTEM, llm.build_user(v, level, msg, history, excerpt),
                                               cfg.chat_max_output_tokens)
    except Exception:  # noqa: BLE001 timeout, HTTP error, bad payload: all mean "use the rule reply"
        return None, "LLM_ERROR", 0, 0, None
    out = llm.clip(raw)
    model = out.model or "unknown"
    bad = llm.postcheck(out, v)
    if bad:
        return None, bad, tin, tout, model
    _CACHE[key] = str(out)
    if len(_CACHE) > 200:
        _CACHE.popitem(last=False)
    return str(out), None, tin, tout, model


async def _extra_reply(db: AsyncSession, v: rules.ItemView, msg: str, pv_id: UUID,
                       item_id: UUID) -> tuple[str | None, int, int, str | None]:
    """The unverified second part. Anything wrong (no model, budget, error, guard) means: no second part, the first stays."""
    cfg = get_settings()
    client = llm.get_chat_llm()
    if client is None:
        return None, 0, 0, None
    key = (today(), pv_id, item_id, "extra", rules.norm(msg))
    if key in _CACHE:
        return _CACHE[key], 0, 0, "cache"
    used = await db.scalar(select(func.coalesce(func.sum(m.ChatMessage.tokens_in + m.ChatMessage.tokens_out), 0)).where(
        m.ChatMessage.created_at >= day_start_utc())) or 0
    if used >= cfg.chat_daily_token_budget:
        return None, 0, 0, None
    try:
        raw, tin, tout = await client.complete(llm.EXTRA_SYSTEM, llm.build_extra_user(v, msg), cfg.chat_max_output_tokens)
    except Exception:  # noqa: BLE001 timeout, HTTP error, bad payload
        return None, 0, 0, None
    out = llm.clip(raw)
    if llm.postcheck_extra(out, v):
        return None, tin, tout, out.model or None
    _CACHE[key] = str(out)
    if len(_CACHE) > 200:
        _CACHE.popitem(last=False)
    return str(out), tin, tout, out.model or None


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
        return _reply(prev.text, prev.hint_level or 0, [], prev.blocked_reason, prev.mode, prev.hint_level if prev.action == "hint" else None)

    if body.action == "explain" and not answered:
        raise ApiError(409, "NOT_ANSWERED", "Em hãy trả lời câu này trước, rồi Habit sẽ giải thích nhé")
    if body.action == "hint" and answered:
        raise ApiError(409, "ALREADY_ANSWERED", "Câu này đã nộp rồi, em bấm “Habit giải thích” để xem lời giải nhé")
    if body.action == "ask" and not (body.message or "").strip() and not body.quick:
        raise ApiError(422, "MESSAGE_REQUIRED", "Em hãy nhập câu hỏi")
    per_item = await db.scalar(select(func.count()).where(
        m.ChatMessage.session_id == sess, m.ChatMessage.role == "assistant", m.ChatMessage.action != "hint")) or 0  # hints have their own limit
    per_day = await db.scalar(select(func.count()).select_from(m.ChatMessage).join(
        m.ChatSession, m.ChatSession.id == m.ChatMessage.session_id).where(
        m.ChatSession.student_id == user.id, m.ChatMessage.role == "assistant", m.ChatMessage.action != "hint",
        m.ChatMessage.created_at >= day_start_utc())) or 0
    if body.action != "hint" and (per_item >= cfg.chat_max_msgs_per_item or per_day >= cfg.chat_max_msgs_per_day):
        raise ApiError(429, "CHAT_LIMIT", "Hôm nay em hỏi nhiều rồi, thử tự làm nhé!")

    quick = body.quick if body.action == "ask" else None
    label = dict(rules.SUGGESTIONS).get(quick or "", "")
    msg = label if quick else rules.redact((body.message or "").strip()) if body.action == "ask" else ""
    used = await db.scalar(select(func.count()).where(
        m.ChatMessage.session_id == sess, m.ChatMessage.action == "hint", m.ChatMessage.role == "assistant")) or 0
    if body.action == "hint" and used >= cfg.hint_max_per_item:
        raise ApiError(429, "HINT_LIMIT", f"Em đã dùng hết {cfg.hint_max_per_item} gợi ý cho câu này. Em thử làm và nộp bài nhé!")
    n = used + 1 if body.action == "hint" else 0  # which hint this press is (1..HINT_MAX_PER_ITEM)
    seen = {int(lv or 0): n for lv, n in (await db.execute(select(m.ChatMessage.hint_level, func.count()).where(
        m.ChatMessage.session_id == sess, m.ChatMessage.role == "assistant", m.ChatMessage.hint_level.is_not(None))
        .group_by(m.ChatMessage.hint_level))).all()}  # how often each level was already shown: rotate, never repeat
    prefs = await personalization.get_prefs(db, user.id) if personalization.on() else {}
    text, level, refs, reason = rules.decide(v, body.action, msg, used, small="chia_nho_tung_buoc" in prefs,
                                             table_first="uu_tien_bang_so_lieu" in prefs, quick=quick, seen=seen, turn=per_item)
    mode, tin, tout, used_model, open_review = "rule", 0, 0, None, None
    cards = review.raw_cards(pv.snapshot)
    progress = await review.state(db, a.id, user.id) if cards else None
    unseen = {c["id"] for c in cards} - {str(i) for i in (progress.seen_ids if progress else [])}
    pointed = False
    fixed = body.action == "hint" and bool(v.hints) and n <= 3  # AI-drafted question: hints 1..3 are fixed, never reworded
    if body.action == "ask" and cards and (quick == "start" or any(k in f" {rules.norm(msg)} " for k in REVIEW_ASK)):
        # "I have not studied this" / "where do I start": point at the matching review card instead of a generic hint
        open_review = review.best_card(pv.snapshot, f"{v.stem} {msg}", unseen) or cards[0]["id"]
        title = next(c["payload"]["title"] for c in cards if c["id"] == open_review)
        text, level, refs, reason = (f"Em xem thẻ ôn “{title}” trước nhé, ngắn thôi. Em đã xem {len(cards) - len(unseen)}/{len(cards)} thẻ ôn."
                                     if unseen else f"Em đã xem hết thẻ ôn rồi. Em mở lại thẻ “{title}” nếu cần nhắc kiến thức."), 0, [], None
        pointed = True
    elif body.action == "hint" and cards:
        open_review = review.best_card(pv.snapshot, v.stem, unseen)  # a hint during the quiz can lead back to the matching review card
    if fixed:
        text, level, refs = v.hints[n - 1], n, []
        if rules.leak(text, v):  # defence in depth: drafts were checked when written, the answer key may have been edited since
            text, level, refs, _ = rules.decide(v, "hint", "", used, seen=seen)
    offtopic = reason == "OFFTOPIC"  # no keyword hit is not a verdict: in llm mode the model decides, with the approved lesson
    chatty = body.action == "ask" and not quick and rules.smalltalk(msg) is not None  # greeting or thanks: no model, no tokens
    if body.action == "hint" and n > 3:
        # hints 4..10: more specific each time. The model writes them (same guards as any reply); on any problem the last fixed hint
        # is repeated with a pointer back to the source.
        last = v.hints[2] if v.hints else rules.hint(v, 3, small="chia_nho_tung_buoc" in prefs)[0]
        where = rules.read_where(v) if n >= 8 else ""  # the most detailed hints say which row and column to read
        text, level, refs, reason = last + (f" {where}" if where else "") + GUIDE, n, [], None
        if cfg.chat_mode == "llm":
            ask = f"Cho em gợi ý số {n}, cụ thể hơn các gợi ý trước, không nói đáp án." + (f" Chỉ đúng dòng và cột cần đọc: {where}" if where else "")
            excerpt = " ".join(t for _, _, t in v.blocks)
            out, fb, tin, tout, used_model = await _llm_reply(db, v, n, ask, text, excerpt, sess, (today(), pv.id, body.item_id, n, "hint"))
            if out is not None:
                text, mode = out, "llm"
            else:
                reason = fb
    elif body.action != "explain" and not chatty and not fixed and not pointed:
        if cfg.chat_mode == "llm" and (reason is None or offtopic) and not quick:
            excerpt = " ".join(t for _, _, t in (refs or v.blocks))
            key = (today(), pv.id, body.item_id, level, rules.norm(msg))
            out, fb, tin, tout, used_model = await _llm_reply(db, v, level, msg, text, excerpt, sess, key)
            if out is not None:
                text, mode, reason = out, "llm", None
            else:
                reason = fb or reason
                if offtopic:  # the model was blocked or down: do not claim the question is outside the lesson, give a way to start
                    text, refs = rules.hint(v, min(used + 1, 3), small="chia_nho_tung_buoc" in prefs)
                    level = min(used + 1, 3)
        extra_ok = cfg.chat_ai_extra and body.action == "ask" and reason is None and not offtopic and not quick
        if cfg.chat_mode == "llm" and extra_ok:
            extra, etin, etout, emodel = await _extra_reply(db, v, msg, pv.id, body.item_id)
            tin, tout = tin + etin, tout + etout
            if extra:
                text, mode, used_model = text + EXTRA_SEP + extra, "llm", used_model or emodel

    if cfg.chat_mode == "llm" and mode == "rule" and body.action != "explain":
        log.info("habit: rule reply instead of llm, reason=%s action=%s", reason or ("smalltalk" if chatty else "fixed_or_quick"), body.action)
    try:
        async with db.begin_nested():
            db.add(m.ChatMessage(session_id=sess, role="user", action=body.action, text=msg or "(gợi ý)", mode="rule"))
            db.add(m.ChatMessage(session_id=sess, role="assistant", action=body.action, text=text,
                                 hint_level=level or None, mode=mode, model=used_model, blocked_reason=reason,
                                 tokens_in=tin, tokens_out=tout, request_id=body.request_id))
    except IntegrityError:  # double click: the other request won
        again = (await db.execute(select(m.ChatMessage).where(
            m.ChatMessage.session_id == sess, m.ChatMessage.request_id == body.request_id,
            m.ChatMessage.role == "assistant"))).scalar_one()
        return _reply(again.text, again.hint_level or 0, [], again.blocked_reason, again.mode, again.hint_level if again.action == "hint" else None)
    if body.action == "hint":
        await bump(db, user.id, hints=1)
    await db.commit()
    return _reply(text, level, refs, reason, mode, n or None, open_review)


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
    advice = await personalization.skill_advice(db, user.id) if personalization.on() else {}
    prefs = await personalization.get_prefs(db, user.id) if advice else {}
    attempted = set(right) | set(await student._attempts(db, a.id, user.id))  # noqa: SLF001

    def item_out(i: dict[str, Any]) -> HabitItem:
        iid = UUID(i["id"])
        got = None if iid in attempted else advice.get(i["payload"]["skill"])
        preview = None
        if got == "REVIEW":
            preview = rules.hint(rules.build_view(pv.snapshot, i), 1, small="chia_nho_tung_buoc" in prefs)[0]
        return HabitItem(item_id=iid, hints_used=min((hints.get(iid) or (0, 0))[0], cfg.hint_max_per_item), hints_max=cfg.hint_max_per_item,
                         advice=got, preview=preview)

    return HabitOut(
        streak=streak, today_goal=cfg.habit_daily_goal, today_done=done.get(today(), 0),
        badges=[HabitBadge(code=c, label=BADGES[c]) for c in earned],
        hints_available=[item_out(i) for i in student._items(pv.snapshot)])  # noqa: SLF001


async def chat_stats(db: AsyncSession) -> dict[str, Any]:
    """Counters for /admin/survey/stats. No message text."""
    by_model = {r[0]: r[1] for r in (await db.execute(select(m.ChatMessage.model, func.count()).where(
        m.ChatMessage.role == "assistant", m.ChatMessage.model.is_not(None)).group_by(m.ChatMessage.model))).all()}
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
            "chat_by_model": by_model,
            "chat_tokens_in": sum(int(r[3]) for r in rows), "chat_tokens_out": sum(int(r[4]) for r in rows)}
