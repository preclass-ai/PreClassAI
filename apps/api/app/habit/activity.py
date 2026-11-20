"""Study-day bookkeeping. Kept free of the student module so `student.submit_attempt` can call it without a cycle."""

from datetime import UTC, date, datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m

VN = timezone(timedelta(hours=7))  # Asia/Ho_Chi_Minh has no DST, so a fixed offset avoids a tzdata dependency


def today() -> date:
    return datetime.now(VN).date()


def day_start_utc() -> datetime:
    return datetime.combine(today(), datetime.min.time(), VN).astimezone(UTC)


async def bump(db: AsyncSession, student_id: UUID, items: int = 0, hints: int = 0) -> None:
    t = m.StudyActivity.__table__
    ins = pg_insert(m.StudyActivity).values(student_id=student_id, day=today(), items_answered=items, hints_used=hints)
    await db.execute(ins.on_conflict_do_update(
        index_elements=[t.c.student_id, t.c.day],
        set_={"items_answered": t.c.items_answered + items, "hints_used": t.c.hints_used + hints}))
