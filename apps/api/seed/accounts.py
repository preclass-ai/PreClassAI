"""Extra DEMO accounts (20 teachers, 20 students). Idempotent: safe to run on every start / on an already-seeded DB.

Teachers gv01..gv20@preclass.local join both demo classes (so they can assign); students HS10-16..HS10-35 join 10A1.
gv01 also owns the empty grade-12 class 12A1 (a full upper-secondary set: 10, 11, 12).
Same demo password as the rest of the seed. Never runs under APP_ENV=production.
"""
import asyncio
from collections.abc import Callable

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import get_settings
from app.db import models as m
from app.ids import uid
from seed.passwords import MissingSeedPassword
from seed.passwords import hashes as pw_hashes

DOMAIN = "preclass.local"
TEACHERS = [f"gv{i:02d}" for i in range(1, 21)]
STUDENTS = [f"HS10-{i}" for i in range(16, 36)]


async def ensure_class_12(conn: AsyncConnection) -> None:
    """Class 12A1 for gv01, idempotent. Needs gv01: a DB without the demo accounts gets it on the run that creates them."""
    teacher = uid("user:gv01")
    if (await conn.execute(select(m.AppUser.id).where(m.AppUser.id == teacher))).first() is None:
        return
    cid = uid("class:12A1")
    await conn.execute(insert(m.Class.__table__).values(id=cid, code="12A1", grade=12, name="12A1").on_conflict_do_nothing())  # type: ignore[arg-type]
    await conn.execute(insert(m.ClassMember.__table__).values(class_id=cid, user_id=teacher, role_in_class="TEACHER")  # type: ignore[arg-type]
                       .on_conflict_do_nothing())


async def ensure_accounts(conn: AsyncConnection, get_hashes: Callable[[], dict[str, str]]) -> int:
    """Insert missing accounts; return how many users were added."""
    classes = {c: uid(f"class:{c}") for c in ("10A1", "11A1")}
    if (await conn.execute(select(m.Class.id).where(m.Class.id == classes["10A1"]))).first() is None:
        return 0  # empty DB: the main seed creates the classes and calls us afterwards
    await ensure_class_12(conn)
    ids = [uid(f"user:{n}") for n in TEACHERS + STUDENTS]
    have = (await conn.execute(select(func.count()).select_from(m.AppUser).where(m.AppUser.id.in_(ids)))).scalar_one()
    if have == len(ids):
        return 0  # nothing to add: do not even require the seed passwords (a restart must not depend on them)
    pw_by_role = get_hashes()
    users = [{"id": uid(f"user:{t}"), "email": f"{t}@{DOMAIN}", "login_code": None,
              "display_name": f"Giáo viên {t[2:]}", "role": "TEACHER", "password_hash": pw_by_role["TEACHER"]} for t in TEACHERS]
    users += [{"id": uid(f"user:{s}"), "email": None, "login_code": s,
               "display_name": f"Học sinh {s[2:]}", "role": "STUDENT", "password_hash": pw_by_role["STUDENT"]} for s in STUDENTS]
    members = [{"class_id": cid, "user_id": uid(f"user:{t}"), "role_in_class": "TEACHER"}
               for t in TEACHERS for cid in classes.values()]
    members += [{"class_id": classes["10A1"], "user_id": uid(f"user:{s}"), "role_in_class": "STUDENT"} for s in STUDENTS]
    u, cm = m.AppUser.__table__, m.ClassMember.__table__
    added = (await conn.execute(insert(u).values(users).on_conflict_do_nothing().returning(u.c.id))).fetchall()  # type: ignore[arg-type]
    await conn.execute(insert(cm).values(members).on_conflict_do_nothing())  # type: ignore[arg-type]
    await ensure_class_12(conn)  # gv01 exists now
    return len(added)


async def main() -> None:
    if get_settings().app_env.lower() in ("production", "prod"):
        raise SystemExit("Refusing: APP_ENV=production (demo accounts share a known password).")
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        try:
            n = await ensure_accounts(conn, lambda: pw_hashes(get_settings().app_env))
        except MissingSeedPassword as e:
            n = 0
            print(f"WARNING: extra demo accounts NOT created: {e}. The API starts anyway.")
    await engine.dispose()
    print(f"demo accounts added: {n}")


if __name__ == "__main__":
    asyncio.run(main())
