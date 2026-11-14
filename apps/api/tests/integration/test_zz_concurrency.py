"""Publish vs concurrent edit/review (D-001 #5). Real connections, real commits: this file runs after the isolated
tests (and before the migration test) because it leaves committed rows behind; every session starts from a reset DB."""

import asyncio
from collections.abc import AsyncIterator

import httpx
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.auth import login_limiter
from app.db.session import get_engine
from app.generation import background_runner, run_job
from tests.conftest import login
from tests.integration.test_generation import blocks, generate, new_lesson
from tests.integration.test_publish import approve_all, lesson_version, review

pytestmark = pytest.mark.db


@pytest.fixture
async def real_client(db_ready: None) -> AsyncIterator[httpx.AsyncClient]:
    from app.main import app

    async def _inline(job_id: object) -> None:
        async with async_sessionmaker(get_engine(), expire_on_commit=False)() as s:
            await run_job(s, job_id)  # type: ignore[arg-type]

    app.dependency_overrides[background_runner] = lambda: _inline  # no get_db override: requests really commit
    login_limiter.reset()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t",
                                 headers={"X-PreClass-CSRF": "1"}) as c:
        yield c
    app.dependency_overrides.clear()


async def _approved_lesson(c: httpx.AsyncClient) -> tuple[str, str, int]:
    lesson, rev = await new_lesson(c)
    assert (await generate(c, lesson)).status_code == 202
    await approve_all(c, rev)
    return lesson, rev, await lesson_version(c, lesson)


@pytest.mark.parametrize("round_", range(2))
async def test_publish_and_edit_race_has_exactly_one_winner(real_client: httpx.AsyncClient, round_: int) -> None:
    c = real_client
    await login(c, "gv.dia@preclass.local")
    lesson, rev, version = await _approved_lesson(c)
    target = next(b for b in await blocks(c, rev) if b["kind"] == "paragraph")
    pub, edit = await asyncio.gather(
        c.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": True, "version": version}),
        c.patch(f"/v1/blocks/{target['id']}", json={"payload": {"text": f"Sửa đồng thời {round_}"}, "version": target["version"]}),
    )
    published, edited = pub.status_code == 201, edit.status_code == 200
    assert published != edited, (pub.status_code, edit.status_code)  # never both, never neither
    if published:
        assert edit.json()["code"] == "REVISION_LOCKED"
        snap = (await c.get(f"/v1/lessons/{lesson}")).json()["publishedVersionId"]
        assert snap == pub.json()["id"]
        after = next(b for b in await blocks(c, rev) if b["id"] == target["id"])
        assert after["payload"] == target["payload"] and after["reviewStatus"] == "APPROVED"  # what was approved is what shipped
    else:
        assert pub.json()["code"] == "PUBLISH_BLOCKED" and target["id"] in pub.json()["blockIds"]
        assert (await c.get(f"/v1/lessons/{lesson}")).json()["publishedVersionId"] is None


@pytest.mark.parametrize("round_", range(2))
async def test_publish_and_review_race_has_exactly_one_winner(real_client: httpx.AsyncClient, round_: int) -> None:
    c = real_client
    await login(c, "gv.dia@preclass.local")
    lesson, rev, version = await _approved_lesson(c)
    target = next(b for b in await blocks(c, rev) if b["kind"] == "paragraph")
    pub, rej = await asyncio.gather(
        c.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": True, "version": version}),
        review(c, target["id"], target["contentHash"], "REJECT", f"race {round_}"),
    )
    published, rejected = pub.status_code == 201, rej.status_code == 201
    assert published != rejected, (pub.status_code, rej.status_code)
    if published:
        assert rej.json()["code"] == "REVISION_LOCKED"
    else:
        assert pub.json()["code"] == "PUBLISH_BLOCKED"
