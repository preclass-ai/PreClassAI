import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from seed.accounts import ensure_accounts
from tests.conftest import login


async def test_extra_demo_accounts_are_idempotent_and_can_log_in(client: httpx.AsyncClient, db: AsyncSession) -> None:
    conn = await db.connection()
    assert await ensure_accounts(conn, "preclass-demo") == 40
    assert await ensure_accounts(conn, "preclass-demo") == 0  # Render runs it on every start: second run adds nothing
    assert (await login(client, "gv20@preclass.local")).status_code == 200
    me = (await client.get("/v1/me")).json()
    assert me["role"] == "TEACHER"
    client.cookies.clear()
    assert (await login(client, "HS10-35")).status_code == 200
    assert len((await client.get("/v1/student/assignments")).json()["items"]) >= 1  # in 10A1, sees the seeded assignment
