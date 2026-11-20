"""Classes for the public demo: the survey class KS (what anonymous guests see) and the private E2E class. Idempotent; demo only.

Run after `seed.seed` (Render start command, reset script). Guests are created at runtime by POST /v1/auth/guest.

KS gets ONLY the published lessons of the seed (never a lesson somebody published later, e.g. during E2E runs), and any other
unanswered assignment found in KS is removed. The E2E class is where automated tests give their lessons: guests are never members.
"""
import asyncio
import os
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from sqlalchemy import delete, exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import get_settings
from app.db import models as m
from app.ids import uid
from seed.lessons import LESSONS
from seed.passwords import MIN_LENGTH, MissingSeedPassword

SEED_PUBLISHED_LESSONS = [uid(f"{lesson['key']}:lesson") for lesson in LESSONS if lesson["publish"]]
E2E_CLASS = "E2E"
E2E_STUDENT = "E2E-1"  # login code of the one student automated tests use (password: E2E_STUDENT_PASSWORD)


async def ensure_survey_class(conn: AsyncConnection, code: str) -> int:
    """Create the class and assign the seed's published lessons; returns the number of assignments added."""
    teacher = (await conn.execute(select(m.AppUser.id).where(m.AppUser.email == "gv.dia@preclass.local"))).scalar()
    if teacher is None:
        return 0  # empty DB: seed.seed first
    cid = uid(f"class:{code}")
    await conn.execute(insert(m.Class.__table__).values(id=cid, code=code, grade=10).on_conflict_do_nothing())  # type: ignore[arg-type]
    await conn.execute(insert(m.ClassMember.__table__).values(  # type: ignore[arg-type]
        class_id=cid, user_id=teacher, role_in_class="TEACHER").on_conflict_do_nothing())
    seed_pvs = select(m.PublishedVersion.id).join(
        m.LessonRevision, m.LessonRevision.id == m.PublishedVersion.lesson_revision_id).where(
        m.PublishedVersion.state == "ACTIVE", m.LessonRevision.lesson_id.in_(SEED_PUBLISHED_LESSONS))
    # Anything else that ended up in KS (older versions of this script assigned every published lesson): drop it unless answered.
    A = m.Assignment.__table__  # noqa: N806
    await conn.execute(delete(A).where(
        A.c.class_id == cid, A.c.published_version_id.not_in(seed_pvs),
        ~exists().where(m.StudentAttempt.__table__.c.assignment_id == A.c.id)))
    pvs = (await conn.execute(seed_pvs)).scalars().all()
    have = set((await conn.execute(select(m.Assignment.published_version_id).where(m.Assignment.class_id == cid))).scalars())
    now, added = datetime.now(UTC), 0
    for pv in pvs:
        if pv not in have:
            await conn.execute(insert(A).values(  # type: ignore[arg-type]
                id=uid(f"{pv}:assignment:{code}"), published_version_id=pv, class_id=cid,
                open_at=now - timedelta(days=1), due_at=now + timedelta(days=365)))
            added += 1
    return added


async def ensure_e2e_class(conn: AsyncConnection, student_password: str | None) -> str:
    """Class E2E (teacher gv.dia) and, only when a password is given, the student E2E-1 in it. Returns what it did."""
    teacher = (await conn.execute(select(m.AppUser.id).where(m.AppUser.email == "gv.dia@preclass.local"))).scalar()
    if teacher is None:
        return "no seed yet"
    cid = uid(f"class:{E2E_CLASS}")
    await conn.execute(insert(m.Class.__table__).values(id=cid, code=E2E_CLASS, grade=10).on_conflict_do_nothing())  # type: ignore[arg-type]
    await conn.execute(insert(m.ClassMember.__table__).values(  # type: ignore[arg-type]
        class_id=cid, user_id=teacher, role_in_class="TEACHER").on_conflict_do_nothing())
    if not student_password:
        return "class only (no E2E_STUDENT_PASSWORD)"
    if len(student_password) < MIN_LENGTH:
        raise MissingSeedPassword(f"E2E_STUDENT_PASSWORD needs at least {MIN_LENGTH} characters")
    sid, pw = uid(f"user:{E2E_STUDENT}"), PasswordHasher().hash(student_password)
    u = m.AppUser.__table__
    await conn.execute(insert(u).values(  # type: ignore[arg-type]
        id=sid, login_code=E2E_STUDENT, display_name="Học sinh kiểm thử E2E", role="STUDENT", password_hash=pw,
    ).on_conflict_do_update(index_elements=[u.c.id], set_={"password_hash": pw, "is_active": True}))  # follows a rotated password
    await conn.execute(insert(m.ClassMember.__table__).values(  # type: ignore[arg-type]
        class_id=cid, user_id=sid, role_in_class="STUDENT").on_conflict_do_nothing())
    return f"class + student {E2E_STUDENT}"


async def main() -> None:
    cfg = get_settings()
    if cfg.app_env.lower() in ("production", "prod"):
        raise SystemExit("Refusing: APP_ENV=production (demo content only).")
    engine = create_async_engine(cfg.database_url)
    async with engine.begin() as conn:
        n = await ensure_survey_class(conn, cfg.guest_class_code)
        print(f"survey class {cfg.guest_class_code}: assignments added: {n}")
        try:
            print(f"e2e class: {await ensure_e2e_class(conn, os.environ.get('E2E_STUDENT_PASSWORD'))}")
        except MissingSeedPassword as e:
            print(f"WARNING: E2E student NOT created: {e}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
