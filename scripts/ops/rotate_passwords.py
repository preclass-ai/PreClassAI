"""Rotate the passwords of the EXISTING seed accounts in a deployed demo database. Prints counts only, never a password.

Run from apps/api, with every secret set only in this shell session (never in a file, never on the command line):

    cd apps/api
    $env:DATABASE_URL = "<Neon direct connection string>"
    $env:APP_ENV = "demo"
    $env:SEED_TEACHER_PASSWORD  = "<>= 12 characters>"
    $env:SEED_REVIEWER_PASSWORD = "<>= 12 characters>"
    $env:SEED_ADMIN_PASSWORD    = "<>= 12 characters>"
    # optional: $env:SEED_STUDENT_PASSWORD = "..." (without it, seed students get a random secret that is thrown away,
    # i.e. they can no longer log in with a password: use anonymous guests)
    uv run python ../../scripts/ops/rotate_passwords.py            # asks you to type ROTATE

TEACHER/REVIEWER/ADMIN/STUDENT accounts are updated; anonymous guests are untouched (they have no password).
Every session of a rotated account is revoked. Weak (< 12 characters) or missing passwords are refused.
"""
import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.getcwd())  # run from apps/api
from app.config import get_settings  # noqa: E402
from seed.passwords import ROLE_ENV, hashes  # noqa: E402


async def rotate(url: str, by_role: dict[str, str]) -> dict[str, int]:
    engine = create_async_engine(url)
    counts: dict[str, int] = {}
    async with engine.begin() as conn:
        for role, pw_hash in by_role.items():
            ids = (await conn.execute(
                text("UPDATE app_user SET password_hash = :h WHERE role = :r AND NOT is_guest RETURNING id"),
                {"h": pw_hash, "r": role})).scalars().all()
            counts[role] = len(ids)
            if ids:
                await conn.execute(
                    text("UPDATE session SET revoked_at = now() WHERE user_id = ANY(:ids) AND revoked_at IS NULL"), {"ids": ids})
    await engine.dispose()
    return counts


def main() -> None:
    if "DATABASE_URL" not in os.environ:
        sys.exit("Set DATABASE_URL in this shell first.")
    missing = [n for n in ROLE_ENV.values() if not os.environ.get(n)]
    if missing:
        sys.exit("Set in this shell: " + ", ".join(missing))
    cfg = get_settings()
    by_role = hashes("demo")  # validates length >= 12; students: SEED_STUDENT_PASSWORD or a random throw-away secret
    print(f"Target database host: {cfg.database_url.split('@')[-1].split('/')[0]}")
    if input("Type ROTATE to change the passwords of all seed accounts: ").strip() != "ROTATE":
        sys.exit("Cancelled.")
    for role, n in asyncio.run(rotate(cfg.database_url, by_role)).items():
        print(f"{role}: {n} accounts updated")


if __name__ == "__main__":
    main()
