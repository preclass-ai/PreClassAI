# ruff: noqa: E501
"""Quick review before the quiz (not scored): the approved cards in the snapshot, and the student's progress through them.

The progress row is the student's learning memory: HABIT AI reads it to know how far the student got."""

from typing import Any
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.errors import ApiError
from app.habit import rules
from app.lessonplan.audience import student_text
from app.schemas import ReviewCardPayload, ReviewProgressIn, ReviewState, StudentReviewCard


def raw_cards(snap: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted((b for b in snap["blocks"] if b["kind"] == "review_card"), key=lambda b: b["position"])


def _words(v: Any) -> Any:
    if isinstance(v, str):
        return student_text(v)
    if isinstance(v, list):
        return [_words(x) for x in v]
    if isinstance(v, dict):
        return {k: _words(x) for k, x in v.items()}
    return v


def cards(snap: dict[str, Any]) -> list[StudentReviewCard]:
    return [StudentReviewCard(id=UUID(b["id"]), position=b["position"], **ReviewCardPayload.model_validate(_words(b["payload"])).model_dump())
            for b in raw_cards(snap)]


async def state(db: AsyncSession, assignment_id: UUID, student_id: UUID) -> ReviewState:
    row = await db.get(m.ReviewProgress, (assignment_id, student_id))
    if row is None:
        return ReviewState()
    return ReviewState(choice=row.choice, seen_ids=list(row.seen_ids), checks={k: bool(v) for k, v in row.checks.items()},
                       reviewed=row.reviewed)


async def save(db: AsyncSession, snap: dict[str, Any], assignment_id: UUID, student_id: UUID, body: ReviewProgressIn) -> ReviewState:
    ids = {b["id"] for b in raw_cards(snap)}
    if any(str(i) not in ids for i in body.seen_ids or []) or any(k not in ids for k in body.checks or {}):
        raise ApiError(422, "INVALID_CARD", "Thẻ ôn này không có trong bài")
    cur = await state(db, assignment_id, student_id)
    seen = list(dict.fromkeys([*cur.seen_ids, *(body.seen_ids or [])]))  # progress only moves forward
    checks = {**cur.checks, **(body.checks or {})}
    vals: dict[str, Any] = {"choice": body.choice or cur.choice, "seen_ids": seen, "checks": checks, "reviewed": cur.reviewed or bool(body.reviewed)}
    t = m.ReviewProgress.__table__
    await db.execute(pg_insert(m.ReviewProgress).values(assignment_id=assignment_id, student_id=student_id, **vals)
                     .on_conflict_do_update(index_elements=[t.c.assignment_id, t.c.student_id], set_={**vals, "updated_at": func.clock_timestamp()}))
    await db.commit()
    return await state(db, assignment_id, student_id)


def best_card(snap: dict[str, Any], text: str, unseen: set[str] | None = None) -> str | None:
    """The review card whose title and points share the most words with `text` (a question stem or a student message)."""
    q = {t for t in rules.norm(text).split() if len(t) > 2 and t not in rules.STOP}
    scored = [(len(q & set(rules.norm(" ".join([b["payload"]["title"], *b["payload"]["points"]])).split())), b["id"]) for b in raw_cards(snap)]
    scored = [x for x in scored if x[0] > 0]
    pool = [x for x in scored if unseen is None or x[1] in unseen] or scored
    return max(pool)[1] if pool else None
