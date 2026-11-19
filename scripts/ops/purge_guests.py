"""Remove inactive anonymous survey guests. NEVER runs automatically.

    cd apps/api
    $env:DATABASE_URL = "<connection string>"                      # PowerShell, this session only
    uv run python ../../scripts/ops/purge_guests.py --dry-run      # what would happen, changes nothing
    uv run python ../../scripts/ops/purge_guests.py --days 30      # asks you to type PURGE

A guest with no attempts is deleted (account, sessions, class membership). Attempts are append-only in the database
(trigger), so a guest who answered cannot be deleted: the account is DEACTIVATED instead (sessions revoked, cannot
resume) and its survey_code stays so the survey export remains linkable. "Inactive" = last_seen_at (else created_at)
older than N days.
"""
import argparse
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.getcwd())  # run from apps/api
from app.config import get_settings  # noqa: E402

STALE = """SELECT u.id, EXISTS (SELECT 1 FROM student_attempt a WHERE a.student_id = u.id) AS has_attempts
           FROM app_user u WHERE u.is_guest AND u.is_active
             AND COALESCE(u.last_seen_at, u.created_at) < now() - make_interval(days => :days)"""


async def run(days: int, dry: bool) -> None:
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        rows = (await conn.execute(text(STALE), {"days": days})).all()
        gone = [r.id for r in rows if not r.has_attempts]
        keep = [r.id for r in rows if r.has_attempts]
        print(f"inactive > {days} days: {len(rows)} guests -> delete {len(gone)}, deactivate {len(keep)} (have attempts)")
        if dry:
            print("dry-run: nothing changed")
        else:
            for uid_ in gone:
                p = {"u": uid_}
                await conn.execute(text("DELETE FROM session WHERE user_id = :u"), p)
                await conn.execute(text("DELETE FROM class_member WHERE user_id = :u"), p)
                await conn.execute(text("DELETE FROM app_user WHERE id = :u AND is_guest"), p)
            for uid_ in keep:
                p = {"u": uid_}
                await conn.execute(text("UPDATE session SET revoked_at = now() WHERE user_id = :u AND revoked_at IS NULL"), p)
                await conn.execute(text("UPDATE app_user SET is_active = false WHERE id = :u AND is_guest"), p)
            print("done")
    await engine.dispose()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if "DATABASE_URL" not in os.environ:
        sys.exit("Set DATABASE_URL in this shell first.")
    if not a.dry_run and input("Type PURGE to continue: ").strip() != "PURGE":
        sys.exit("Cancelled.")
    asyncio.run(run(a.days, a.dry_run))


if __name__ == "__main__":
    main()
