"""Personalization (ADR-0013): options the STUDENT chooses, plus rule-based advice from the student's own results.

Nothing here infers, stores or exposes a trait or health label of the student: the only
inputs are the options they switched on and their first-attempt results / hint use per skill, recomputed on every call.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.blocks import NOT_FOUND
from app.config import get_settings
from app.db import models as m
from app.schemas import PreferencesIn, PreferencesOut

BOOL_KEYS = ("chia_nho_tung_buoc", "uu_tien_bang_so_lieu", "uu_tien_giai_thich", "nhac_tien_do", "focus_mode_used")
REVIEW_MIN_ATTEMPTS, REVIEW_WRONG_RATE = 2, 0.5  # a skill the student keeps getting wrong first time
QUIET_MIN_ATTEMPTS, QUIET_GOOD_RATE = 3, 0.8  # right first time without a hint


def enabled() -> None:
    if not get_settings().personalization_enabled:
        raise NOT_FOUND


def on() -> bool:
    return get_settings().personalization_enabled


async def get_prefs(db: AsyncSession, student_id: UUID) -> dict[str, str]:
    rows = (await db.execute(select(m.StudentPreference.key, m.StudentPreference.value).where(
        m.StudentPreference.student_id == student_id))).all()
    return {k: v for k, v in rows}


def _check(key: str, value: str) -> None:
    from app.errors import ApiError

    ok = value in ("off", "5", "10") if key == "hen_gio_tap_trung" else value in ("on", "off")
    if not ok:
        raise ApiError(422, "VALIDATION_ERROR", "Giá trị lựa chọn không hợp lệ", f"{key}: {value}")


async def put_prefs(db: AsyncSession, user: CurrentUser, body: PreferencesIn) -> PreferencesOut:
    enabled()
    for key, value in body.preferences.items():
        _check(key, value)
    for key, value in body.preferences.items():
        if value == "off":
            await db.execute(delete(m.StudentPreference).where(
                m.StudentPreference.student_id == user.id, m.StudentPreference.key == key))
        else:
            ins = pg_insert(m.StudentPreference).values(student_id=user.id, key=key, value=value)
            await db.execute(ins.on_conflict_do_update(index_elements=["student_id", "key"],
                                                       set_={"value": value, "updated_at": func.now()}))
    await db.commit()
    return PreferencesOut(preferences=await get_prefs(db, user.id))


async def read_prefs(db: AsyncSession, user: CurrentUser) -> PreferencesOut:
    enabled()
    return PreferencesOut(preferences=await get_prefs(db, user.id))


async def reset_prefs(db: AsyncSession, user: CurrentUser) -> PreferencesOut:
    enabled()
    await db.execute(delete(m.StudentPreference).where(m.StudentPreference.student_id == user.id))
    await db.commit()
    return PreferencesOut(preferences={})


async def skill_advice(db: AsyncSession, student_id: UUID) -> dict[str, str]:
    """skill -> REVIEW | QUIET from this student's own attempts and hints (rules only; nothing is stored)."""
    rows = (await db.execute(
        select(m.StudentAttempt.item_block_id, m.StudentAttempt.is_correct, m.PublishedVersion.snapshot)
        .join(m.Assignment, m.Assignment.id == m.StudentAttempt.assignment_id)
        .join(m.PublishedVersion, m.PublishedVersion.id == m.Assignment.published_version_id)
        .where(m.StudentAttempt.student_id == student_id, m.StudentAttempt.is_correct.is_not(None)))).all()
    hinted = set((await db.execute(
        select(m.ChatSession.item_block_id).join(m.ChatMessage, m.ChatMessage.session_id == m.ChatSession.id)
        .where(m.ChatSession.student_id == student_id, m.ChatMessage.action == "hint"))).scalars())
    stats: dict[str, list[int]] = {}  # skill -> [attempts, wrong, right-without-hint]
    for item_id, ok, snap in rows:
        item: Any = next((b for b in snap["blocks"] if b["id"] == str(item_id)), None)
        if item is None:
            continue
        s = stats.setdefault(item["payload"]["skill"], [0, 0, 0])
        s[0] += 1
        s[1] += 0 if ok else 1
        s[2] += 1 if ok and item_id not in hinted else 0
    out: dict[str, str] = {}
    for skill, (n, wrong, good) in stats.items():
        if n >= REVIEW_MIN_ATTEMPTS and wrong / n >= REVIEW_WRONG_RATE:
            out[skill] = "REVIEW"
        elif n >= QUIET_MIN_ATTEMPTS and good / n >= QUIET_GOOD_RATE:
            out[skill] = "QUIET"
    return out
