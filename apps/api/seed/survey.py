"""Survey class for anonymous guests: class KS + every ACTIVE published lesson assigned to it. Idempotent; demo only.

Run after `seed.seed` (Render start command, reset script). Guests are created at runtime by POST /v1/auth/guest.
"""
import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import get_settings
from app.db import models as m
from app.ids import uid


async def ensure_survey_class(conn: AsyncConnection, code: str) -> int:
    """Create the class and assign missing published versions; returns the number of assignments added."""
    teacher = (await conn.execute(select(m.AppUser.id).where(m.AppUser.email == "gv.dia@preclass.local"))).scalar()
    if teacher is None:
        return 0  # empty DB: seed.seed first
    cid = uid(f"class:{code}")
    await conn.execute(insert(m.Class.__table__).values(id=cid, code=code, grade=10).on_conflict_do_nothing())  # type: ignore[arg-type]
    await conn.execute(insert(m.ClassMember.__table__).values(  # type: ignore[arg-type]
        class_id=cid, user_id=teacher, role_in_class="TEACHER").on_conflict_do_nothing())
    pvs = (await conn.execute(select(m.PublishedVersion.id).where(m.PublishedVersion.state == "ACTIVE"))).scalars().all()
    have = set((await conn.execute(select(m.Assignment.published_version_id).where(m.Assignment.class_id == cid))).scalars())
    now, added = datetime.now(UTC), 0
    for pv in pvs:
        if pv not in have:
            await conn.execute(insert(m.Assignment.__table__).values(  # type: ignore[arg-type]
                id=uid(f"{pv}:assignment:{code}"), published_version_id=pv, class_id=cid,
                open_at=now - timedelta(days=1), due_at=now + timedelta(days=365)))
            added += 1
    return added


async def main() -> None:
    cfg = get_settings()
    if cfg.app_env.lower() in ("production", "prod"):
        raise SystemExit("Refusing: APP_ENV=production (demo content only).")
    engine = create_async_engine(cfg.database_url)
    async with engine.begin() as conn:
        n = await ensure_survey_class(conn, cfg.guest_class_code)
    await engine.dispose()
    print(f"survey class {cfg.guest_class_code}: assignments added: {n}")


if __name__ == "__main__":
    asyncio.run(main())
