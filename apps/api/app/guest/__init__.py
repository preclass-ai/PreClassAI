"""Anonymous survey guests: one throw-away STUDENT account per person, identified only by a survey code (KS-XXXX).

No name, e-mail or IP is stored. Guests are STUDENT accounts in the survey class, so every teacher/admin route already
answers them 403 and the student whitelist (PR-08) applies unchanged.
"""

import csv
import io
import logging
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import LoginLimiter
from app.config import get_settings
from app.db import models as m
from app.errors import ApiError
from app.ids import uid

ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O/1/I: codes are copied by hand from a screen
PREFIX = "KS-"
UNUSABLE_HASH = "!guest"  # not an argon2 hash: password login can never succeed
NOT_ENABLED = ApiError(404, "NOT_FOUND", "Không tìm thấy")
log = logging.getLogger("preclass.guest")
WARN_AT = 0.8  # log a warning when a guest limit is 80% used

create_limiter = LoginLimiter(window_s=3600)  # counts every guest created from an IP in the last hour
resume_limiter = LoginLimiter(max_failures=5, window_s=900)  # wrong codes per IP per 15 minutes


def require_enabled() -> None:
    if not get_settings().guest_access_enabled:
        raise NOT_ENABLED


def new_code() -> str:
    return PREFIX + "".join(secrets.choice(ALPHABET) for _ in range(4))


def normalize_code(raw: str) -> str:
    return raw.strip().upper().replace(" ", "")


async def survey_class(db: AsyncSession) -> m.Class:
    cls = await db.scalar(select(m.Class).where(m.Class.code == get_settings().guest_class_code))
    if cls is None:
        raise ApiError(503, "GUEST_NOT_CONFIGURED", "Lớp khảo sát chưa được cấu hình")
    return cls


async def active_guests(db: AsyncSession) -> int:
    """Guests seen (or created) in the last 14 days."""
    return int(await db.scalar(select(func.count()).select_from(m.AppUser).where(
        m.AppUser.is_guest.is_(True),
        func.coalesce(m.AppUser.last_seen_at, m.AppUser.created_at) > datetime.now(UTC) - timedelta(days=14))) or 0)


async def stats(db: AsyncSession) -> dict[str, int]:
    cfg = get_settings()
    last_hour = await db.scalar(select(func.count()).select_from(m.AppUser).where(
        m.AppUser.is_guest.is_(True), m.AppUser.created_at > datetime.now(UTC) - timedelta(hours=1)))
    return {"active_guests": await active_guests(db), "created_last_hour": int(last_hour or 0),
            "max_active": cfg.guest_max_active, "create_per_hour_per_ip": cfg.guest_create_per_hour}


async def create_guest(db: AsyncSession, ip: str) -> m.AppUser:
    cfg = get_settings()
    create_limiter.check(ip, cfg.guest_create_per_hour)
    cls = await survey_class(db)
    active = await active_guests(db)
    if active >= cfg.guest_max_active:
        raise ApiError(503, "GUEST_CAPACITY", "Hệ thống khảo sát đang quá tải, vui lòng thử lại sau")
    for _ in range(20):
        code = new_code()
        if await db.scalar(select(m.AppUser.id).where(m.AppUser.survey_code == code)) is None:
            break
    else:  # pragma: no cover - 32^4 codes: practically unreachable below GUEST_MAX_ACTIVE
        raise ApiError(503, "GUEST_CAPACITY", "Không tạo được mã khảo sát, vui lòng thử lại")
    user = m.AppUser(login_code=code, survey_code=code, display_name=f"Khách {code[len(PREFIX):]}", role="STUDENT",
                     password_hash=UNUSABLE_HASH, is_guest=True, last_seen_at=datetime.now(UTC))
    db.add(user)
    await db.flush()
    db.add(m.ClassMember(class_id=cls.id, user_id=user.id, role_in_class="STUDENT"))
    create_limiter.fail(ip)
    # Counts only: never the IP or the code in a log line.
    if len(create_limiter.hits[ip]) >= WARN_AT * cfg.guest_create_per_hour:
        log.warning("guest creation from one client at %d/%d per hour", len(create_limiter.hits[ip]), cfg.guest_create_per_hour)
    if active + 1 >= WARN_AT * cfg.guest_max_active:
        log.warning("active guests %d/%d (>= 80%% of GUEST_MAX_ACTIVE)", active + 1, cfg.guest_max_active)
    return user


async def find_guest(db: AsyncSession, raw_code: str, ip: str) -> m.AppUser:
    resume_limiter.check(ip)
    user = await db.scalar(select(m.AppUser).where(
        m.AppUser.survey_code == normalize_code(raw_code), m.AppUser.is_guest.is_(True), m.AppUser.is_active.is_(True)))
    if user is None:
        resume_limiter.fail(ip)
        raise ApiError(404, "NOT_FOUND", "Không tìm thấy mã khảo sát này")
    resume_limiter.reset(ip)
    user.last_seen_at = datetime.now(UTC)
    return user


async def assignment_for_lesson(db: AsyncSession, lesson_key: str | None) -> UUID | None:
    """Assignment (in the survey class) of the lesson whose seed slug is `lesson_key`, e.g. dan-so-vung."""
    if not lesson_key:
        return None
    return await db.scalar(
        select(m.Assignment.id)
        .join(m.PublishedVersion, m.PublishedVersion.id == m.Assignment.published_version_id)
        .join(m.LessonRevision, m.LessonRevision.id == m.PublishedVersion.lesson_revision_id)
        .join(m.Class, m.Class.id == m.Assignment.class_id)
        .where(m.LessonRevision.lesson_id == uid(f"{lesson_key}:lesson"), m.PublishedVersion.state == "ACTIVE",
               m.Class.code == get_settings().guest_class_code)
        .limit(1))


def _safe(cell: str) -> str:
    return "'" + cell if cell[:1] in ("=", "+", "-", "@") else cell  # CSV formula injection


async def export_csv(db: AsyncSession) -> str:
    """One row per guest answer (+ Habit counters): survey_code, lesson, item, is_correct, answered_at.
    Attempts are write-once, so each row is the FIRST (and only) attempt. Nothing else identifies the person."""
    rows = (await db.execute(
        select(m.AppUser.survey_code, m.PublishedVersion.snapshot, m.StudentAttempt.item_block_id,
               m.StudentAttempt.is_correct, m.StudentAttempt.created_at, m.StudentAttempt.student_id)
        .join(m.AppUser, m.AppUser.id == m.StudentAttempt.student_id)
        .join(m.Assignment, m.Assignment.id == m.StudentAttempt.assignment_id)
        .join(m.PublishedVersion, m.PublishedVersion.id == m.Assignment.published_version_id)
        .where(m.AppUser.is_guest.is_(True))
        .order_by(m.AppUser.survey_code, m.StudentAttempt.created_at))).all()
    A, S = m.ChatMessage, m.ChatSession  # noqa: N806 Habit counters per (student, item): counts only, never message text
    chat = {(r[0], r[1]): r[2:] for r in (await db.execute(
        select(S.student_id, S.item_block_id,
               func.count().filter(A.action == "hint"), func.coalesce(func.max(A.hint_level), 0),
               func.count().filter(A.action == "ask"), func.bool_or(A.action == "explain"),
               func.count().filter(A.blocked_reason.is_not(None)))
        .join(S, S.id == A.session_id).where(A.role == "assistant").group_by(S.student_id, S.item_block_id))).all()}
    P = m.StudentPreference  # noqa: N806 options the student switched on, as flags (no other attribute of the student)
    prefs: dict[Any, dict[str, str]] = {}
    for sid, key, value in (await db.execute(select(P.student_id, P.key, P.value))).all():
        prefs.setdefault(sid, {})[key] = value
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\n")
    w.writerow(["survey_code", "lesson", "item", "first_attempt_is_correct", "answered_at_utc", "hints_used",
                "max_hint_level", "chat_asks", "used_explain", "blocked_count", "pref_chia_nho", "pref_hen_gio_phut",
                "pref_bang_so_lieu", "pref_giai_thich", "pref_nhac_tien_do", "focus_mode_used"])
    for code, snap, item_id, ok, at, student_id in rows:
        hints, top, asks, expl, blocked = chat.get((student_id, item_id), (0, 0, 0, False, 0))
        p = prefs.get(student_id, {})
        items: list[dict[str, Any]] = [b for b in snap["blocks"] if b["kind"] == "worksheet_item"]
        n = next((i for i, b in enumerate(items, start=1) if b["id"] == str(item_id)), 0)
        w.writerow([code, _safe(str(snap["title"])), f"Câu {n}", "" if ok is None else str(ok).lower(),
                    at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    hints, top, asks, str(bool(expl)).lower(), blocked,
                    int("chia_nho_tung_buoc" in p), p.get("hen_gio_tap_trung", "0"), int("uu_tien_bang_so_lieu" in p),
                    int("uu_tien_giai_thich" in p), int("nhac_tien_do" in p), int("focus_mode_used" in p)])
    return out.getvalue()
