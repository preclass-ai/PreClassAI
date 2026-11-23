"""READ ONLY: which class are guests put in (GUEST_CLASS_CODE), and which classes does gv01@preclass.local own?

Run:  cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/ks_class.py
Prints id, join code, display name, owner (teacher members), student count and the active assignments of each class.
The transaction is READ ONLY (Postgres refuses any write); DATABASE_URL and passwords are never printed.
"""

import asyncio
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from sqlalchemy import select, text  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import models as m  # noqa: E402

TEACHER_EMAIL = "gv01@preclass.local"


async def show(conn: AsyncConnection, cls: Any) -> None:
    owners = (await conn.execute(
        select(m.AppUser.email, m.AppUser.display_name)
        .join(m.ClassMember, m.ClassMember.user_id == m.AppUser.id)
        .where(m.ClassMember.class_id == cls.id, m.ClassMember.role_in_class == "TEACHER").order_by(m.AppUser.email))).all()
    students = (await conn.execute(
        select(m.AppUser.is_guest)
        .join(m.ClassMember, m.ClassMember.user_id == m.AppUser.id)
        .where(m.ClassMember.class_id == cls.id, m.ClassMember.role_in_class == "STUDENT"))).all()
    rows = (await conn.execute(
        select(m.Lesson.title, m.Assignment.open_at, m.Assignment.due_at)
        .join(m.LessonRevision, m.LessonRevision.lesson_id == m.Lesson.id)
        .join(m.PublishedVersion, m.PublishedVersion.lesson_revision_id == m.LessonRevision.id)
        .join(m.Assignment, m.Assignment.published_version_id == m.PublishedVersion.id)
        .where(m.Assignment.class_id == cls.id, m.Assignment.cancelled_at.is_(None))
        .order_by(m.Assignment.due_at))).all()
    print(f"  id           {cls.id}")
    print(f"  join code    {cls.code}")
    print(f"  display name {cls.name or '(none, shows the code)'}  grade {cls.grade}")
    print("  owner        " + (", ".join(f"{e or '?'} ({n})" for e, n in owners) or "(no TEACHER member)"))
    print(f"  students     {len(students)} (guests {sum(1 for (g,) in students if g)})")
    print(f"  assignments  {len(rows)}")
    for title, open_at, due_at in rows:
        print(f"    - {title} | open {open_at:%Y-%m-%d} | due {due_at:%Y-%m-%d}")


async def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows console is cp1258
    cfg = get_settings()
    engine = create_async_engine(cfg.database_url)
    async with engine.connect() as conn:
        await conn.execute(text("SET TRANSACTION READ ONLY"))
        print(f"== Guest class (GUEST_CLASS_CODE = {cfg.guest_class_code!r})")
        guest = (await conn.execute(select(m.Class).where(m.Class.code == cfg.guest_class_code))).first()
        if guest is None:
            print("  NOT FOUND: guests would get GUEST_NOT_CONFIGURED")
        else:
            await show(conn, guest)
        print(f"\n== Classes of {TEACHER_EMAIL}")
        teacher = await conn.scalar(select(m.AppUser.id).where(m.AppUser.email == TEACHER_EMAIL))
        if teacher is None:
            print("  NOT FOUND: no such user")
        else:
            classes = (await conn.execute(
                select(m.Class).join(m.ClassMember, m.ClassMember.class_id == m.Class.id)
                .where(m.ClassMember.user_id == teacher, m.ClassMember.role_in_class == "TEACHER").order_by(m.Class.code))).all()
            print(f"  {len(classes)} class(es)")
            for c in classes:
                print(f"\n  -- {c.code}")
                await show(conn, c)
        await conn.rollback()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
