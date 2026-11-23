import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from seed.accounts import ensure_accounts
from seed.passwords import hashes
from tests.conftest import login
from tests.integration.test_lesson_plans import H, upload
from tests.plan_fixtures import plan_docx


async def test_extra_demo_accounts_are_idempotent_and_can_log_in(client: httpx.AsyncClient, db: AsyncSession) -> None:
    conn = await db.connection()
    assert await ensure_accounts(conn, lambda: hashes("development", {})) == 40
    assert await ensure_accounts(conn, lambda: hashes("development", {})) == 0  # Render runs it on every start: second run adds nothing
    assert (await login(client, "gv20@preclass.local")).status_code == 200
    me = (await client.get("/v1/me")).json()
    assert me["role"] == "TEACHER"
    client.cookies.clear()
    assert (await login(client, "HS10-35")).status_code == 200
    assert len((await client.get("/v1/student/assignments")).json()["items"]) >= 1  # in 10A1, sees the seeded assignment


async def test_gv01_owns_grade_12_class_and_can_make_a_grade_12_lesson(client: httpx.AsyncClient, db: AsyncSession) -> None:
    conn = await db.connection()
    for _ in range(2):  # twice: the class is created once
        await ensure_accounts(conn, lambda: hashes("development", {}))
    await login(client, "gv01@preclass.local")
    items = (await client.get("/v1/classes")).json()["items"]
    assert sorted((i["code"], i["grade"], i["studentCount"]) for i in items) == [("10A1", 10, 35), ("11A1", 11, 15), ("12A1", 12, 0)]
    (p,) = await upload(client, plan_docx(grade=12))  # "Môn Địa lí 12": the lesson made from it is grade 12 (DB check widened by 0016)
    out = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()
    assert (await client.get(f"/v1/lessons/{out['lessonId']}")).json()["grade"] == 12
