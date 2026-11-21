"""Migration 0007 is applied: lesson plan tables exist, the Địa lí competency catalogue is seeded, constraints bite."""

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = pytest.mark.db


async def test_competency_catalogue_is_seeded_for_geography_only(db: AsyncSession) -> None:
    rows = (await db.execute(text("SELECT subject, code FROM subject_competency ORDER BY code"))).all()
    assert [tuple(r) for r in rows] == [("DIA_LI", "NHAN_THUC"), ("DIA_LI", "TIM_HIEU"), ("DIA_LI", "VAN_DUNG")]


@pytest.mark.parametrize("table", ["lesson_plan", "lesson_section", "objective", "extracted_mcq"])
async def test_tables_exist_and_are_empty(db: AsyncSession, table: str) -> None:
    assert await db.scalar(text(f"SELECT count(*) FROM {table}")) == 0


async def test_answer_and_activity_values_are_constrained(db: AsyncSession) -> None:
    names = {r[0] for r in (await db.execute(text("SELECT conname FROM pg_constraint WHERE conname LIKE 'ck_mcq_%' OR conname LIKE 'ck_section_%'"))).all()}
    assert names == {"ck_mcq_correct", "ck_mcq_source", "ck_mcq_conf", "ck_section_activity", "ck_section_sub"}


async def test_only_geography_is_an_active_subject(db: AsyncSession) -> None:
    rows = (await db.execute(text("SELECT code FROM subject WHERE active"))).all()
    assert [r[0] for r in rows] == ["DIA_LI"]
    assert await db.scalar(text("SELECT count(*) FROM subject")) >= 10
