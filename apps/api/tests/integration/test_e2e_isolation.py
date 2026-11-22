"""The survey class KS shows guests ONLY the seed's published lessons; automated tests live in the private E2E class."""

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.guest import create_limiter, resume_limiter
from app.ids import uid
from seed.survey import E2E_CLASS, E2E_STUDENT, ensure_e2e_class, ensure_survey_class
from tests.conftest import login
from tests.integration.test_generation import generate, new_lesson
from tests.integration.test_publish import approve_all, lesson_version

pytestmark = pytest.mark.db


async def ks_titles(db: AsyncSession) -> list[str]:
    rows = await db.execute(text(
        "SELECT pv.snapshot->>'title' FROM assignment a JOIN class c ON c.id = a.class_id "
        "JOIN published_version pv ON pv.id = a.published_version_id WHERE c.code = 'KS' ORDER BY 1"))
    return [r[0] for r in rows]


async def test_ks_gets_only_seed_lessons_and_prunes_foreign_unanswered_assignments(
        client: httpx.AsyncClient, db: AsyncSession) -> None:
    conn = await db.connection()
    assert await ensure_survey_class(conn, "KS") == 1
    await login(client, "gv.dia@preclass.local")
    lesson, rev = await new_lesson(client)  # a lesson published later, e.g. by an E2E run
    await generate(client, lesson)
    await approve_all(client, rev)
    pub = (await client.post(f"/v1/revisions/{rev}/publish",
                             json={"confirmChecked": True, "version": await lesson_version(client, lesson)})).json()
    # Older script versions assigned every published lesson to KS: simulate that leftover.
    await db.execute(text(
        "INSERT INTO assignment(published_version_id, class_id, open_at, due_at) "
        "SELECT :pv, id, now() - interval '1 day', now() + interval '30 days' FROM class WHERE code = 'KS'"), {"pv": pub["id"]})
    assert "Bài thử" in await ks_titles(db)
    assert await ensure_survey_class(conn, "KS") == 0
    assert await ks_titles(db) == ["Phân bố dân cư theo vùng"]  # only the seed lesson is left
    assert await ensure_survey_class(conn, "KS") == 0  # idempotent


async def test_seed_lesson_has_the_same_deadline_for_the_teacher_class_and_the_survey_class(db: AsyncSession) -> None:
    """Reviewer report: the teacher (class 10A1) saw 20/12/2026, a guest (class KS) saw 20/11/2027 for the same lesson."""
    await ensure_survey_class(await db.connection(), "KS")
    dues = (await db.execute(text(
        "SELECT c.code, a.due_at FROM assignment a JOIN class c ON c.id = a.class_id "
        "JOIN published_version pv ON pv.id = a.published_version_id "
        "WHERE c.code IN ('10A1', 'KS') AND pv.snapshot->>'title' = 'Phân bố dân cư theo vùng'"))).all()
    assert {code for code, _ in dues} == {"10A1", "KS"}
    assert len({due for _, due in dues}) == 1


async def test_e2e_class_has_a_student_only_with_a_password_and_guests_never_join_it(
        client: httpx.AsyncClient, db: AsyncSession, monkeypatch: pytest.MonkeyPatch) -> None:
    conn = await db.connection()
    assert (await ensure_e2e_class(conn, None)).startswith("class only")
    assert await db.scalar(text("SELECT count(*) FROM app_user WHERE login_code = :c"), {"c": E2E_STUDENT}) == 0
    with pytest.raises(Exception, match="at least 12"):
        await ensure_e2e_class(conn, "short")
    assert (await ensure_e2e_class(conn, "e2e-student-pass-1")).startswith("class + student")
    assert await ensure_e2e_class(conn, "e2e-student-pass-2")  # a rotated password is applied, not duplicated
    assert await db.scalar(text("SELECT count(*) FROM app_user WHERE login_code = :c"), {"c": E2E_STUDENT}) == 1
    assert (await login(client, E2E_STUDENT, "e2e-student-pass-1")).status_code == 401
    assert (await login(client, E2E_STUDENT, "e2e-student-pass-2")).status_code == 200

    monkeypatch.setenv("GUEST_ACCESS_ENABLED", "true")
    get_settings.cache_clear()
    create_limiter.reset()
    resume_limiter.reset()
    await ensure_survey_class(conn, "KS")
    try:
        client.cookies.clear()
        g = (await client.post("/v1/auth/guest", json={})).json()
        e2e_id = str(uid(f"class:{E2E_CLASS}"))
        assert e2e_id not in g["user"]["classIds"] and len(g["user"]["classIds"]) == 1
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
        create_limiter.reset()
