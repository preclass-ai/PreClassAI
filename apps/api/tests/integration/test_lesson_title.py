"""Renaming: the lesson title and goal (mutable), an assignment's own student-facing name, and the default title built from a plan."""

import httpx
import pytest

from app.lessonplan.service import default_title
from tests.conftest import login
from tests.integration.test_assign_practice import A_URL
from tests.integration.test_lesson_plans import H, upload
from tests.integration.test_student import ASSIGN, detail
from tests.plan_fixtures import plan_docx

pytestmark = pytest.mark.db


def test_default_title_is_the_plans_own_title() -> None:
    long = "bài 4. " + "x" * 200
    assert default_title("Chuẩn bị: bài 4. Sự hình thành Trái Đất") == "Bài 4. Sự hình thành Trái Đất"
    assert default_title("  Bài  4.   Vỏ Trái Đất ") == "Bài 4. Vỏ Trái Đất"
    assert default_title("") == "Bài chuẩn bị trước giờ học" and len(default_title(long)) == 120


async def test_plan_lesson_gets_the_plans_title_and_is_found_again_after_a_rename(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    (p,) = await upload(client, plan_docx())
    out = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()
    lesson = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()
    assert lesson["title"] == "CHỦ ĐỀ MẪU" and not lesson["title"].startswith("Chuẩn bị")
    ok = await client.patch(f"/v1/lessons/{out['lessonId']}", json={"title": "Tên mới của bài"}, headers=H)
    assert ok.status_code == 200
    assert (await client.get(f"/v1/lesson-plans/{p['id']}")).json()["lessonId"] == out["lessonId"]  # link does not depend on the title
    assert (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).status_code == 409  # no second lesson


async def test_patch_lesson_checks_owner_and_length_and_logs_history(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    (p,) = await upload(client, plan_docx())
    lid = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()["lessonId"]
    url = f"/v1/lessons/{lid}"
    for bad in ("", "  ", "ab", " ab ", "x" * 121):
        assert (await client.patch(url, json={"title": bad}, headers=H)).status_code == 422, bad
    r = await client.patch(url, json={"title": "   Bài   mới  ", "goal": "  Mục tiêu mới  "}, headers=H)
    assert r.status_code == 200 and r.json()["title"] == "Bài mới" and r.json()["goal"] == "Mục tiêu mới"
    assert (await client.patch(url, json={"goal": ""}, headers=H)).json()["goal"] is None  # empty clears the goal
    assert (await client.patch(url, json={}, headers=H)).json()["title"] == "Bài mới"  # nothing sent, nothing changed
    ev = [e for e in (await client.get(f"{url}/history")).json()["events"] if e["operation"] == "RENAME"]
    assert ev and any(e["before"] == {"title": "CHỦ ĐỀ MẪU"} and e["after"] == {"title": "Bài mới"} for e in ev)
    assert all(e["actorName"] for e in ev)
    await login(client, "gv.khac@preclass.local")  # another teacher
    assert (await client.patch(url, json={"title": "Của người khác"}, headers=H)).status_code == 404
    await login(client, "HS10-01")
    assert (await client.patch(url, json={"title": "Học sinh sửa"}, headers=H)).status_code == 403


async def test_student_sees_the_assignments_display_title_not_the_lesson_rename(client: httpx.AsyncClient) -> None:
    d = await detail(client)
    frozen = d["title"]
    await login(client, "gv.dia@preclass.local")
    a = (await client.get(A_URL.rsplit("/", 1)[0])).json()["items"][0]
    renamed = await client.patch(f"/v1/lessons/{a['lessonId']}", json={"title": "Tên bài đã đổi"}, headers=H)
    assert renamed.status_code == 200
    now = (await client.get(A_URL.rsplit("/", 1)[0])).json()["items"][0]
    assert now["lessonTitle"] == "Tên bài đã đổi" and now["studentTitle"] == frozen  # the snapshot did not change
    await login(client, "HS10-01")
    assert (await client.get(f"/v1/student/assignments/{ASSIGN}")).json()["title"] == frozen

    await login(client, "gv.dia@preclass.local")
    r = await client.patch(A_URL, json={"displayTitle": "  Chuẩn bị:  Bài 4  "}, headers=H)
    assert r.status_code == 200 and r.json()["displayTitle"] == "Chuẩn bị: Bài 4" and r.json()["studentTitle"] == "Chuẩn bị: Bài 4"
    assert r.json()["dueAt"] == a["dueAt"]  # renaming alone leaves the due time
    for bad in ("ab", "x" * 121):
        assert (await client.patch(A_URL, json={"displayTitle": bad}, headers=H)).status_code == 422
    assert (await client.patch(A_URL, json={}, headers=H)).status_code == 422
    await login(client, "gv.khac@preclass.local")
    assert (await client.patch(A_URL, json={"displayTitle": "Của người khác"}, headers=H)).status_code == 404
    await login(client, "HS10-01")
    assert (await client.get(f"/v1/student/assignments/{ASSIGN}")).json()["title"] == "Chuẩn bị: Bài 4"
    assert any(i["title"] == "Chuẩn bị: Bài 4" for i in (await client.get("/v1/student/assignments")).json()["items"])

    await login(client, "gv.dia@preclass.local")
    back = await client.patch(A_URL, json={"displayTitle": None}, headers=H)  # null goes back to the published title
    assert back.json()["displayTitle"] is None and back.json()["studentTitle"] == frozen
