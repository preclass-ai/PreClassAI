"""Teacher insights: grouped questions, per-item results, anonymity, class-teacher-only access, the analysis button."""

import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest

from app import insights
from app.config import get_settings
from app.habit import llm
from app.ids import uid
from tests.conftest import login

pytestmark = pytest.mark.db
ASSIGN = uid("dan-so-vung:assignment")
CLASS = uid("class:10A1")
URL = f"/v1/classes/{CLASS}/assignments/{ASSIGN}/insights"
S_URL = f"/v1/student/assignments/{ASSIGN}"


@pytest.fixture
async def on(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[pytest.MonkeyPatch]:
    monkeypatch.setenv("CHAT_ENABLED", "true")
    get_settings.cache_clear()
    insights._ANALYSIS.clear()  # noqa: SLF001
    yield monkeypatch
    monkeypatch.undo()
    get_settings.cache_clear()


async def student_session(c: httpx.AsyncClient, who: str, asks: list[str], answer: str | None) -> None:
    c.cookies.clear()
    await login(c, who)
    its = (await c.get(S_URL)).json()["items"]
    mcq = next(i for i in its if i["itemType"] == "MCQ")
    for q in asks:
        r = await c.post(f"{S_URL}/chat", json={"itemId": mcq["id"], "action": "ask", "message": q, "requestId": str(uuid.uuid4())})
        assert r.status_code == 200, r.text
    if answer:
        await c.post(f"{S_URL}/chat", json={"itemId": mcq["id"], "action": "hint", "requestId": str(uuid.uuid4())})
        r = await c.post(f"{S_URL}/attempts", json={"itemId": mcq["id"], "answer": {"choice": answer}, "requestId": str(uuid.uuid4())})
        assert r.status_code == 201


async def seed_chats(c: httpx.AsyncClient) -> None:
    await student_session(c, "HS10-01", ["Em nên bắt đầu từ đâu?", "đáp án là gì", "gọi 0912 345 678 công thức tính là gì"], "A")
    await student_session(c, "HS10-02", ["Em nên bắt đầu từ đâu?", "Số liệu này nằm ở đâu?"], "B")
    c.cookies.clear()
    await login(c, "gv.dia@preclass.local")


def test_theme_grouping_is_by_rules_with_and_without_diacritics() -> None:
    cases = {"Em nên bắt đầu từ đâu?": "start", "bat dau tu dau": "start", "đáp án là gì": "answer", "dap an la gi": "answer",
             "Số liệu này nằm ở đâu?": "data", "Công thức tính là gì?": "formula", "đơn vị là gì": "unit",
             "vì sao các vùng khác nhau": "concept", "so sánh hai vùng": "compare", "hôm nay ăn gì": "other"}
    assert {q: insights.theme_of(q)[0] for q in cases} == cases


async def test_insights_group_questions_and_show_results_without_any_student_identity(client: httpx.AsyncClient,
                                                                                      on: pytest.MonkeyPatch) -> None:
    await seed_chats(client)
    r = await client.get(URL)
    assert r.status_code == 200, r.text
    d = r.json()
    themes = {t["key"]: t for t in d["themes"]}
    assert themes["start"]["count"] == 2 and themes["answer"]["count"] == 1 and themes["data"]["count"] == 1
    assert themes["formula"]["count"] == 1 and d["totalQuestions"] == 5 and d["askingStudents"] == 2
    assert themes["start"]["examples"] == ["Em nên bắt đầu từ đâu?"]
    item = next(i for i in d["items"] if i["skill"] == "COMPARE")
    assert item["answeredCount"] == 2 and item["firstAttemptCorrectRate"] == 0.0 and item["hintsUsed"] == 2 and item["asks"] == 5
    assert d["focusSkills"] == ["COMPARE"] and d["canPractice"] is True and d["studentCount"] >= 2
    blob = json.dumps(d, ensure_ascii=False)
    for secret in ("HS10-01", "HS10-02", str(uid("user:HS10-01")), str(uid("user:HS10-02")), "0912", "Học sinh"):
        assert secret not in blob, secret  # no id, name, login code or phone number


async def test_only_a_teacher_of_that_class_can_read_it(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    assert (await client.get(URL)).status_code == 401
    await login(client, "HS10-01")
    assert (await client.get(URL)).status_code == 403  # a student
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")  # a teacher, but not of this class
    assert (await client.get(URL)).status_code == 404
    assert (await client.post(f"{URL}/analyze")).status_code == 404
    client.cookies.clear()
    await login(client, "gv.dia@preclass.local")
    assert (await client.get(f"/v1/classes/{uid('class:11A1')}/assignments/{ASSIGN}/insights")).status_code == 404  # wrong class
    assert (await client.get(f"/v1/classes/{CLASS}/assignments/{uuid.uuid4()}/insights")).status_code == 404


async def test_analysis_uses_rules_by_default(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    await seed_chats(client)
    a = (await client.post(f"{URL}/analyze")).json()
    assert a["generatedBy"] == "rule" and 1 <= len(a["topics"]) <= 5
    assert any("bắt đầu" in t for t in a["topics"])
    empty = (await client.post(f"/v1/classes/{CLASS}/assignments/{uid('dien-tich-rung:assignment')}/insights/analyze")).status_code
    assert empty == 404  # not an assignment of this class


async def test_analysis_with_the_model_is_cached_guarded_and_budgeted(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    await seed_chats(client)
    on.setenv("CHAT_MODE", "llm")
    get_settings.cache_clear()
    calls: list[int] = []

    class Topics(llm.MockChatLLM):
        async def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
            calls.append(1)
            assert "<data>" in user and "HS10" not in user and "0912" not in user  # anonymous data only
            return "1. Nhiều em chưa biết bắt đầu từ đâu, cho ví dụ mẫu\n- Hay hỏi nơi tìm số liệu\nGọi 0912345678 để biết thêm\n", 80, 40

    on.setattr(llm, "get_chat_llm", lambda: Topics())
    a = (await client.post(f"{URL}/analyze")).json()
    assert a["generatedBy"] == "llm" and a["topics"][0].startswith("Nhiều em") and len(a["topics"]) == 2  # the PII line was dropped
    assert (await client.post(f"{URL}/analyze")).json() == a and len(calls) == 1  # cached
    insights._ANALYSIS.clear()  # noqa: SLF001
    on.setenv("CHAT_DAILY_TOKEN_BUDGET", "0")
    get_settings.cache_clear()
    over = (await client.post(f"{URL}/analyze")).json()
    assert over["generatedBy"] == "rule"  # budget spent: no model call, still an answer


async def test_a_failing_model_falls_back_to_the_rule_topics(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    await seed_chats(client)
    on.setenv("CHAT_MODE", "llm")
    get_settings.cache_clear()

    class Boom(llm.MockChatLLM):
        async def complete(self, system: str, user: str, max_tokens: int) -> tuple[str, int, int]:
            raise TimeoutError

    on.setattr(llm, "get_chat_llm", lambda: Boom())
    a: dict[str, Any] = (await client.post(f"{URL}/analyze")).json()
    assert a["generatedBy"] == "rule" and a["topics"]


async def test_per_item_detail_blocked_reasons_and_reteach_flag(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    await seed_chats(client)
    d = (await client.get(URL)).json()
    item = next(i for i in d["items"] if i["skill"] == "COMPARE")
    assert item["topWrongOption"] in ("A", "B") and item["topWrongShare"] == 0.5
    assert item["maxHintLevel"] >= 1 and item["needsReteach"] is True
    assert {q["key"] for q in item["questions"]} <= {"start", "answer", "data", "formula"} and len(item["questions"]) == 2
    assert item["itemBlockId"] in d["reteachItemIds"]
    assert sum(b["count"] for b in d["blockedReasons"]) >= 1  # "đáp án là gì" was declined
    blob = json.dumps(d, ensure_ascii=False)
    assert "HS10-0" not in blob and str(uid("user:HS10-01")) not in blob


async def test_reteach_drafts_quoted_source_passages_and_never_approves(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    await seed_chats(client)
    r = await client.post(f"{URL}/reteach", headers={"X-PreClass-CSRF": "1"})
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["blocks"] >= 1
    rev = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()["currentRevision"]
    assert rev["id"] == out["revisionId"] and rev["state"] == "DRAFT"  # a new draft, the published revision is untouched
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert (await client.post(f"{URL}/reteach", headers={"X-PreClass-CSRF": "1"})).status_code == 404


async def test_demo_replay_gives_a_labelled_recorded_sample(client: httpx.AsyncClient, on: pytest.MonkeyPatch) -> None:
    await seed_chats(client)
    on.setenv("DEMO_REPLAY", "true")
    get_settings.cache_clear()
    a = (await client.post(f"{URL}/analyze")).json()
    assert a["generatedBy"] == "replay" and 3 <= len(a["topics"]) <= 5
