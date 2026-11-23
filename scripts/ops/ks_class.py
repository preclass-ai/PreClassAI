"""Which class are guests put in (GUEST_CLASS_CODE), which classes gv01@preclass.local owns, and a safe retitle.

Run:  cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/ks_class.py
        [--retitle "<new>" --lesson-title-like "<text>" [--apply]]

Without flags: READ ONLY report (the transaction is READ ONLY, Postgres refuses any write). Prints id, join code, display
name, owner (teacher members), student count and the active assignments of each class.

--retitle NEW --lesson-title-like TEXT: dry run by default. Lists every lesson whose title contains TEXT (case-insensitive)
and the open assignments of those lessons, old name -> new name. Students read the title frozen in the published snapshot
(immutable), so the script changes only mutable fields: lesson.title and assignment.display_title (which students see first).
With --apply it asks you to type RETITLE, then changes everything in ONE transaction (rolled back on any error) and writes
rename_log rows (who, when, before, after). DATABASE_URL and passwords are never printed.
"""

import argparse
import asyncio
import getpass
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from sqlalchemy import insert, select, text, update  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import models as m  # noqa: E402
from app.schemas import clean_title  # noqa: E402

TEACHER_EMAIL = "gv01@preclass.local"
BS = chr(92)  # LIKE escape character


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


async def retitle(engine: Any, new: str, like: str, apply: bool) -> int:
    """Dry run unless `apply`. Changes lesson.title and assignment.display_title only, never the published snapshot."""
    pattern = "%" + "".join(BS + c if c in BS + "%_" else c for c in like) + "%"  # LIKE wildcards in the text stay literal
    async with engine.begin() as conn:  # one transaction: any error rolls everything back
        lessons = (await conn.execute(select(m.Lesson.id, m.Lesson.title).where(m.Lesson.title.ilike(pattern, escape=BS))
                                      .order_by(m.Lesson.created_at).with_for_update())).all()
        asg = (await conn.execute(
            select(m.Assignment.id, m.Assignment.display_title, m.PublishedVersion.snapshot["title"].as_string(), m.Class.code,
                   m.Lesson.id)
            .join(m.PublishedVersion, m.PublishedVersion.id == m.Assignment.published_version_id)
            .join(m.LessonRevision, m.LessonRevision.id == m.PublishedVersion.lesson_revision_id)
            .join(m.Lesson, m.Lesson.id == m.LessonRevision.lesson_id).join(m.Class, m.Class.id == m.Assignment.class_id)
            .where(m.Lesson.id.in_([i for i, _ in lessons]), m.Assignment.cancelled_at.is_(None))
            .order_by(m.Class.code, m.Assignment.created_at).with_for_update(of=m.Assignment))).all()
        print(f"{'APPLY' if apply else 'DRY RUN'}: new name {new!r}; lessons matching {like!r}: {len(lessons)}; "
              f"open assignments: {len(asg)}")
        for lid, title in lessons:
            print(f"  lesson {lid}: {title!r} -> {new!r}")
        for aid, shown, snap, code, _ in asg:
            print(f"  assignment {aid} (class {code}): students see {(shown or snap)!r} -> {new!r}"
                  + ("" if shown else f"   [frozen in snapshot: {snap!r}, unchanged; display_title is set instead]"))
        if not apply or not (lessons or asg):
            if not apply:
                print("Nothing written. Add --apply to change these rows.")
            await conn.rollback()
            return 0
        if input('Type RETITLE to write these changes: ').strip() != "RETITLE":
            print("Not confirmed, nothing written.")
            await conn.rollback()
            return 1
        who = f"ops:{getpass.getuser()}"
        for lid, title in lessons:
            await conn.execute(update(m.Lesson).where(m.Lesson.id == lid).values(title=new))
            await conn.execute(insert(m.RenameLog).values(target_type="lesson", target_id=lid, field="title", before=title,
                                                          after=new, actor_label=who))
        for aid, shown, *_ in asg:
            await conn.execute(update(m.Assignment).where(m.Assignment.id == aid).values(display_title=new))
            await conn.execute(insert(m.RenameLog).values(target_type="assignment", target_id=aid, field="display_title",
                                                          before=shown, after=new, actor_label=who))
        print(f"Written by {who}: {len(lessons)} lesson(s), {len(asg)} assignment(s); see rename_log.")
    return 0


async def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]  # Windows console is cp1258
    sys.stderr.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--retitle", metavar="NEW", help="new student-facing name (3 to 120 characters)")
    ap.add_argument("--lesson-title-like", metavar="TEXT", help="lessons whose title contains TEXT (case-insensitive)")
    ap.add_argument("--apply", action="store_true", help="write (asks for RETITLE); default is a dry run")
    args = ap.parse_args()
    if bool(args.retitle) != bool(args.lesson_title_like) or (args.apply and not args.retitle):
        ap.error("--retitle and --lesson-title-like go together; --apply needs both")
    try:
        new = clean_title(args.retitle) if args.retitle else ""
    except ValueError as e:
        ap.error(str(e))
    cfg = get_settings()
    engine = create_async_engine(cfg.database_url)
    if args.retitle:
        try:
            code = await retitle(engine, new, args.lesson_title_like.strip(), args.apply)
        finally:
            await engine.dispose()
        return code
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
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
