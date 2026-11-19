"""Extra DEMO accounts (20 teachers, 20 students). Idempotent: safe to run on every start / on an already-seeded DB.

Teachers gv01..gv20@preclass.local join both demo classes (so they can assign); students HS10-16..HS10-35 join 10A1.
Same demo password as the rest of the seed. Never runs under APP_ENV=production.
"""
import asyncio
import os

from argon2 import PasswordHasher
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import get_settings
from app.db import models as m
from app.ids import uid

DOMAIN = "preclass.local"
TEACHERS = [f"gv{i:02d}" for i in range(1, 21)]
STUDENTS = [f"HS10-{i}" for i in range(16, 36)]


async def ensure_accounts(conn: AsyncConnection, password: str) -> int:
    """Insert missing accounts; return how many users were added."""
    classes = {c: uid(f"class:{c}") for c in ("10A1", "11A1")}
    if (await conn.execute(select(m.Class.id).where(m.Class.id == classes["10A1"]))).first() is None:
        return 0  # empty DB: the main seed creates the classes and calls us afterwards
    pw = PasswordHasher().hash(password)
    users = [{"id": uid(f"user:{t}"), "email": f"{t}@{DOMAIN}", "login_code": None,
              "display_name": f"Giáo viên {t[2:]} (minh họa)", "role": "TEACHER", "password_hash": pw} for t in TEACHERS]
    users += [{"id": uid(f"user:{s}"), "email": None, "login_code": s,
               "display_name": f"Học sinh {s[2:]} (minh họa)", "role": "STUDENT", "password_hash": pw} for s in STUDENTS]
    members = [{"class_id": cid, "user_id": uid(f"user:{t}"), "role_in_class": "TEACHER"}
               for t in TEACHERS for cid in classes.values()]
    members += [{"class_id": classes["10A1"], "user_id": uid(f"user:{s}"), "role_in_class": "STUDENT"} for s in STUDENTS]
    u, cm = m.AppUser.__table__, m.ClassMember.__table__
    added = (await conn.execute(insert(u).values(users).on_conflict_do_nothing().returning(u.c.id))).fetchall()  # type: ignore[arg-type]
    await conn.execute(insert(cm).values(members).on_conflict_do_nothing())  # type: ignore[arg-type]
    return len(added)


async def main() -> None:
    if get_settings().app_env.lower() in ("production", "prod"):
        raise SystemExit("Refusing: APP_ENV=production (demo accounts share a known password).")
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        n = await ensure_accounts(conn, os.environ.get("SEED_PASSWORD", "preclass-demo"))  # noqa: S105
    await engine.dispose()
    print(f"demo accounts added: {n}")


if __name__ == "__main__":
    asyncio.run(main())
