"""Wipe the demo database and rebuild it: DROP SCHEMA public -> alembic upgrade head -> demo seed.

Run from apps/api so the app's settings and dependencies are used; DATABASE_URL comes from the environment only
(set it for this shell session, never write it to a file):

    cd apps/api
    $env:DATABASE_URL = "<Neon direct connection string>"   # PowerShell
    uv run python ../../scripts/ops/reset_demo_db.py

Asks you to type RESET. Refuses APP_ENV=production. Destroys every row: demo data only.
"""
import asyncio
import os
import subprocess
import sys
from urllib.parse import urlsplit

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, os.getcwd())  # run from apps/api: import the app package from there
from app.config import get_settings  # noqa: E402


async def drop_schema(url: str) -> None:
    engine = create_async_engine(url)
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
    await engine.dispose()


def main() -> None:
    if "DATABASE_URL" not in os.environ:
        sys.exit("Set DATABASE_URL in this shell first.")
    s = get_settings()
    if s.app_env.lower() in ("production", "prod"):
        sys.exit("Refusing: APP_ENV=production.")
    target = urlsplit(s.database_url)
    print(f"Target: host={target.hostname} db={target.path.lstrip('/')}  (all data will be deleted)")
    if input('Type RESET to continue: ').strip() != "RESET":
        sys.exit("Cancelled.")
    asyncio.run(drop_schema(s.database_url))
    env = {**os.environ, "PYTHONPATH": "."}
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], check=True, env=env)  # noqa: S603
    subprocess.run([sys.executable, "-m", "seed.seed"], check=True, env=env)  # noqa: S603
    print("Demo database reset.")


if __name__ == "__main__":
    main()
