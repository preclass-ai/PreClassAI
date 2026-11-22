"""AI drafts from a lesson plan, end to end: upload -> drafts -> teacher approves -> lesson -> publish -> student review + Habit."""

import asyncio
import json
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID

import httpx
import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app import habit
from app.config import get_settings
from app.generation.providers import ProviderHTTPError
from app.ids import uid
from app.lessonplan import quizgen
from tests.conftest import login
from tests.plan_fixtures import plan_docx

pytestmark = pytest.mark.db
H = {"X-PreClass-CSRF": "1"}
KNOW = (
    "Dân số nước ta năm 2021 là 98,5 triệu người, đứng thứ ba khu vực Đông Nam Á và đứng thứ mười lăm trên thế giới.",
    "Đồng bằng sông Hồng có mật độ dân số cao nhất cả nước, khoảng 1 091 người trên mỗi ki lô mét vuông diện tích.",
    "Dân cư tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi do điều kiện tự nhiên và lịch sử khai thác lãnh thổ.",
    "Tỉ lệ dân thành thị tăng nhanh nhờ quá trình công nghiệp hóa và đô thị hóa diễn ra mạnh mẽ trong những năm gần đây.",
    "Cơ cấu dân số nước ta đang chuyển từ giai đoạn dân số trẻ sang giai đoạn già hóa với tốc độ khá nhanh theo thời gian.",
    "Nguồn lao động dồi dào là thế mạnh nhưng chất lượng lao động còn hạn chế, cần đào tạo nghề cho người lao động nhiều hơn.",
    "Phân bố dân cư chưa hợp lí gây khó khăn cho việc sử dụng lao động và khai thác tài nguyên ở các vùng trung du miền núi.",
    "Chính sách dân số hiện nay chú trọng nâng cao chất lượng dân số bên cạnh việc duy trì mức sinh thay thế hợp lí cho cả nước.",
)


@pytest.fixture
async def gen(monkeypatch: pytest.MonkeyPatch) -> AsyncIterator[pytest.MonkeyPatch]:
    monkeypatch.setenv("QUIZ_GEN_ENABLED", "true")
    monkeypatch.setenv("QUIZ_GEN_MOCK", "true")
    monkeypatch.setenv("QUIZ_GEN_GAP_S", "0")
    monkeypatch.setenv("CHAT_ENABLED", "true")
    get_settings.cache_clear()
    habit._CACHE.clear()  # noqa: SLF001
    yield monkeypatch
    monkeypatch.undo()
    get_settings.cache_clear()


async def upload(c: httpx.AsyncClient) -> dict[str, Any]:
    r = await c.post("/v1/lesson-plans", files={"file": ("plan.docx", plan_docx(knowledge=KNOW))}, headers=H)
    assert r.status_code == 202, r.text
    job = (await c.get(f"/v1/lesson-plans/jobs/{r.json()['id']}")).json()
    assert job["state"] == "done", job
    return dict((await c.get(f"/v1/lesson-plans/{job['planIds'][0]}")).json())


async def test_drafts_are_labelled_unconfirmed_and_never_reach_the_lesson_unless_approved(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    assert p["aiState"] == "done" and p["aiQuizCount"] >= 5 and p["aiReviewCount"] >= 4
    assert p["aiNeedsConfirmationCount"] == p["aiQuizCount"] + p["aiReviewCount"]
    assert p["aiStats"]["quiz"]["valid"] == p["aiQuizCount"] and p["aiStats"]["tokens"] > 0
    items = (await client.get(f"/v1/lesson-plans/{p['id']}/ai-items")).json()["items"]
    quiz = [i for i in items if i["kind"] == "quiz"]
    assert all(i["origin"] == "ai_generated" and i["status"] == "draft" and i["needsConfirmation"] and i["sourceQuote"] for i in items)
    assert all(len(i["payload"]["options"]) == 4 and len(i["payload"]["hints"]) == 3 for i in quiz)

    # nothing approved: the lesson only has the teacher's own confirmed questions
    other = await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)
    assert other.status_code == 201 and other.json()["practiceItems"] == 1  # the one confirmed MCQ of the plan; no AI item
    assert (await client.patch(f"/v1/lesson-plans/{p['id']}/ai-items/{quiz[0]['id']}", json={"status": "approved"}, headers=H)).status_code == 409


async def test_needs_confirmation_count_follows_each_decision(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    """The "N cần xác nhận" line counts drafts still waiting: approved ones drop out, rejected ones are not counted at all."""
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    url = f"/v1/lesson-plans/{p['id']}/ai-items"
    quiz = [i for i in (await client.get(url)).json()["items"] if i["kind"] == "quiz"]
    total = p["aiQuizCount"]
    assert p["aiQuizNeedsConfirmationCount"] == total

    async def plan() -> dict[str, Any]:
        return dict((await client.get(f"/v1/lesson-plans/{p['id']}")).json())

    await client.patch(f"{url}/{quiz[0]['id']}", json={"status": "approved"}, headers=H)
    await client.patch(f"{url}/{quiz[1]['id']}", json={"status": "rejected"}, headers=H)
    now = await plan()
    assert (now["aiQuizCount"], now["aiQuizNeedsConfirmationCount"]) == (total - 1, total - 2)
    edit = {**quiz[0]["payload"], "stem": "Câu hỏi đã được thầy cô sửa lại cho rõ ý hơn?"}
    await client.patch(f"{url}/{quiz[0]['id']}", json={"payload": edit}, headers=H)  # an edit sends it back to draft
    assert (await plan())["aiQuizNeedsConfirmationCount"] == total - 1


async def test_approve_edit_reject_regenerate(client: httpx.AsyncClient, db: AsyncSession, gen: pytest.MonkeyPatch) -> None:
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    items = (await client.get(f"/v1/lesson-plans/{p['id']}/ai-items")).json()["items"]
    quiz = [i for i in items if i["kind"] == "quiz"]
    url = f"/v1/lesson-plans/{p['id']}/ai-items"
    ok = (await client.patch(f"{url}/{quiz[0]['id']}", json={"status": "approved"}, headers=H)).json()
    assert ok["status"] == "approved" and ok["needsConfirmation"] is False
    edited = {**quiz[1]["payload"], "stem": "Câu hỏi đã được thầy cô sửa lại cho rõ ý hơn?"}
    e = (await client.patch(f"{url}/{quiz[1]['id']}", json={"payload": edited}, headers=H)).json()
    assert e["status"] == "draft" and e["payload"]["stem"].startswith("Câu hỏi đã được") and e["needsConfirmation"]
    bad = await client.patch(f"{url}/{quiz[1]['id']}", json={"payload": {**edited, "options": ["chỉ một"]}}, headers=H)
    assert bad.status_code == 422
    assert (await client.patch(f"{url}/{quiz[2]['id']}", json={"status": "rejected"}, headers=H)).json()["status"] == "rejected"
    started: list[object] = []
    gen.setattr(quizgen, "start", lambda pid, spec=None: started.append((pid, spec)))  # the real one runs in its own session, outside this test transaction
    r = await client.post(f"{url}/regenerate", headers=H)
    assert r.status_code == 202 and r.json()["aiState"] == "queued" and len(started) == 1
    assert (await client.post(f"{url}/regenerate", headers=H)).status_code == 409  # already queued
    await quizgen.run_plan(db, UUID(p["id"]), spec=started[0][1])  # what the background task does
    after = (await client.get(url)).json()["items"]
    assert any(i["id"] == quiz[0]["id"] and i["status"] == "approved" for i in after)  # approved stays
    assert not any(i["id"] in (quiz[1]["id"], quiz[2]["id"]) for i in after)  # drafts and rejected ones were replaced
    assert sum(i["kind"] == "quiz" for i in after) == 8  # the approved one plus new drafts, up to QUIZ_GEN_PER_LESSON
    client.cookies.clear()
    await login(client, "gv.khac@preclass.local")
    assert (await client.get(url)).status_code == 404  # someone else's plan


async def test_budget_and_missing_model_skip_without_failing(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    gen.setenv("QUIZ_GEN_DAILY_TOKENS", "1")
    get_settings.cache_clear()
    await login(client, "gv.dia@preclass.local")
    first = await upload(client)  # the first plan may spend the budget...
    second = await upload(client)
    assert first["aiState"] == "done" and second["aiState"] == "skipped" and second["aiStats"]["reason"] == "budget"
    gen.setenv("QUIZ_GEN_MOCK", "false")
    gen.setenv("QUIZ_GEN_DAILY_TOKENS", "100000")
    get_settings.cache_clear()
    gen.setattr(quizgen, "get_client", lambda: None)
    third = await upload(client)
    assert third["aiState"] == "skipped" and third["aiStats"]["reason"] == "no_model" and third["aiQuizCount"] == 0


class BrokenThenGood:
    """First reply is not JSON, the retry is fine: one retry only."""

    def __init__(self) -> None:
        self.calls = 0

    async def complete(self, system: str, user: str, max_tokens: int, timeout: float | None = None) -> tuple[str, int, int]:
        self.calls += 1
        if self.calls % 2 == 1:
            return "xin lỗi, tôi không làm được", 10, 5
        return await quizgen.MockQuizLLM().complete(system, user, max_tokens)


async def test_a_broken_json_reply_is_retried_once(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    gen.setenv("QUIZ_GEN_MOCK", "false")
    get_settings.cache_clear()
    fake = BrokenThenGood()
    gen.setattr(quizgen, "get_client", lambda: fake)
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    assert p["aiState"] == "done" and p["aiStats"]["quiz"]["calls"] == 2 and p["aiQuizCount"] >= 5
    assert fake.calls == 4  # quiz + review, each one retry


async def test_whole_flow_review_cards_gate_and_habit_points_to_a_card(client: httpx.AsyncClient, db: AsyncSession, gen: pytest.MonkeyPatch) -> None:
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    url = f"/v1/lesson-plans/{p['id']}/ai-items"
    items = (await client.get(url)).json()["items"]
    for i in [x for x in items if x["kind"] == "quiz"][:2] + [x for x in items if x["kind"] == "review"][:2]:
        assert (await client.patch(f"{url}/{i['id']}", json={"status": "approved"}, headers=H)).status_code == 200
    out = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()
    rev = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()["currentRevision"]["id"]
    blocks = (await client.get(f"/v1/revisions/{rev}/blocks")).json()["items"]
    assert sum(b["kind"] == "review_card" for b in blocks) == 2
    ai_items = [b for b in blocks if b["kind"] == "worksheet_item" and b["payload"].get("hints")]
    assert len(ai_items) == 2 and all(b["transformation"] == "AI_PROPOSED" for b in ai_items)
    for b in blocks:  # the usual gate: every block is approved one by one
        r = await client.post(f"/v1/blocks/{b['id']}/reviews", json={"action": "APPROVE", "contentHash": b["contentHash"]})
        ev = (await db.execute(text("SELECT rule, evidence FROM validation_result WHERE block_id=:i AND outcome='FAIL'"), {"i": b["id"]})).all() if r.status_code != 201 else []
        assert r.status_code == 201, (b["kind"], ev)
    chk = (await client.get(f"/v1/revisions/{rev}/publish-check")).json()
    assert chk["canPublish"] is True, chk
    ver = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()["currentRevision"]["version"]
    pub = (await client.post(f"/v1/revisions/{rev}/publish", json={"confirmChecked": True, "version": ver})).json()
    asg = await client.post(f"/v1/published/{pub['id']}/assignments", json={
        "classId": str(uid("class:10A1")), "openAt": "2020-01-01T00:00:00+07:00", "dueAt": "2099-01-01T00:00:00+07:00"})
    assert asg.status_code == 201, asg.text
    url_s = f"/v1/student/assignments/{asg.json()['id']}"

    client.cookies.clear()
    await login(client, "HS10-01")
    a = (await client.get(url_s)).json()
    assert len(a["items"]) == 3 and len(a["review"]) == 2 and a["reviewState"]["choice"] is None  # 2 AI questions + the confirmed one
    assert all("hints" not in json.dumps(i) and "correct" not in json.dumps(i) for i in a["items"])  # hints and key stay on the server
    c0, c1 = a["review"][0]["id"], a["review"][1]["id"]
    st = (await client.put(f"{url_s}/review", json={"choice": "not_yet", "seenIds": [c0], "checks": {c0: True}}, headers=H)).json()
    assert st["choice"] == "not_yet" and st["seenIds"] == [c0] and st["checks"] == {c0: True} and st["reviewed"] is False
    st = (await client.put(f"{url_s}/review", json={"seenIds": [c1], "reviewed": True}, headers=H)).json()
    assert st["seenIds"] == [c0, c1] and st["reviewed"] is True and st["choice"] == "not_yet"  # progress only moves forward
    assert (await client.put(f"{url_s}/review", json={"seenIds": ["00000000-0000-4000-8000-000000000001"]}, headers=H)).status_code == 422

    item = next(i for i in a["items"] if i["id"] in {b["id"] for b in ai_items})
    body = {"itemId": item["id"], "action": "ask", "message": "em chưa học bài, em nên bắt đầu từ đâu", "requestId": "11111111-1111-4111-8111-111111111111"}
    r = (await client.post(f"{url_s}/chat", json=body)).json()
    assert r["openReview"] in (c0, c1) and r["source"] == "rule" and "xem hết thẻ ôn" in r["reply"]
    hint = (await client.post(f"{url_s}/chat", json={"itemId": item["id"], "action": "hint", "requestId": "22222222-2222-4222-8222-222222222222"})).json()
    assert hint["hintLevel"] == 1 and hint["reply"] == next(b for b in ai_items if b["id"] == item["id"])["payload"]["hints"][0]  # AI hints are fixed
    done = (await client.post(f"{url_s}/attempts", json={"itemId": item["id"], "answer": {"choice": "A"}, "requestId": "33333333-3333-4333-8333-333333333333"})).json()
    assert done["sourceQuote"] and done["correctAnswer"].startswith(("A.", "B.", "C.", "D.")) and done["explanation"]  # "Theo giáo án: <quote>"


class ReviewBroken:
    """Quiz answers, the review call fails with the given error."""

    def __init__(self, err: BaseException) -> None:
        self.err = err

    async def complete(self, system: str, user: str, max_tokens: int, timeout: float | None = None) -> tuple[str, int, int]:
        if system == quizgen.SYSTEM_REVIEW:
            raise self.err
        return await quizgen.MockQuizLLM().complete(system, user, max_tokens)


@pytest.mark.parametrize("err,status", [(ProviderHTTPError(400, "json_validate_failed"), "400"), (TimeoutError(), "TimeoutError")])
async def test_a_failed_review_does_not_cost_the_quiz(client: httpx.AsyncClient, db: AsyncSession, gen: pytest.MonkeyPatch,
                                                      err: BaseException, status: str) -> None:
    gen.setenv("QUIZ_GEN_MOCK", "false")
    get_settings.cache_clear()
    gen.setattr(quizgen, "get_client", lambda: ReviewBroken(err))
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    assert p["aiState"] == "done" and p["aiQuizCount"] >= 5 and p["aiReviewCount"] == 0  # the quiz is saved
    assert p["aiStats"]["review"] == {"failed": True, "reason": "model_error", "status": status, "failed_models": []}
    assert p["aiStats"]["quiz"]["valid"] == p["aiQuizCount"]
    quiz_ids = {i["id"] for i in (await client.get(f"/v1/lesson-plans/{p['id']}/ai-items")).json()["items"] if i["kind"] == "quiz"}

    # "Tạo lại" with a working model redoes only the review: the quiz drafts keep their ids
    gen.setattr(quizgen, "get_client", lambda: quizgen.MockQuizLLM())
    await quizgen.run_plan(db, UUID(p["id"]))
    after = (await client.get(f"/v1/lesson-plans/{p['id']}")).json()
    items = (await client.get(f"/v1/lesson-plans/{p['id']}/ai-items")).json()["items"]
    assert after["aiReviewCount"] >= 4 and "failed" not in after["aiStats"]["review"]
    assert {i["id"] for i in items if i["kind"] == "quiz"} == quiz_ids


async def test_review_cards_all_rejected_are_marked_not_drafted(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    class FakeQuotes:
        async def complete(self, system: str, user: str, max_tokens: int, timeout: float | None = None) -> tuple[str, int, int]:
            raw, a, b = await quizgen.MockQuizLLM().complete(system, user, max_tokens)
            data = json.loads(raw)
            for c in data["cards"]:
                c["source_sentence_ids"] = []  # a model that ignores the ids and sends text that is not in the plan
                c["source_quote"] = "Một câu hoàn toàn khác không hề có trong giáo án của tiết học này đâu."
            return json.dumps(data, ensure_ascii=False), a, b

    gen.setenv("QUIZ_GEN_MOCK", "false")
    get_settings.cache_clear()
    gen.setattr(quizgen, "get_client", lambda: FakeQuotes())
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    r = p["aiStats"]["review"]
    assert p["aiReviewCount"] == 0 and r["failed"] is True and r["reason"] == "all_rejected" and r["rejected"] == {"quote_not_in_plan": 5}
    assert len(r["quote_scores"]) == 5 and all(isinstance(x, int) and x < 90 for x in r["quote_scores"])  # numbers only
    assert p["aiQuizCount"] >= 5


async def test_unknown_sentence_ids_are_rejected_and_the_server_writes_the_quote(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    class BadIds:
        async def complete(self, system: str, user: str, max_tokens: int, timeout: float | None = None) -> tuple[str, int, int]:
            raw, a, b = await quizgen.MockQuizLLM().complete(system, user, max_tokens)
            data = json.loads(raw)
            for c in data["cards"][:2]:
                c["source_sentence_ids"] = [999]
            return json.dumps(data, ensure_ascii=False), a, b

    gen.setenv("QUIZ_GEN_MOCK", "false")
    get_settings.cache_clear()
    gen.setattr(quizgen, "get_client", lambda: BadIds())
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    assert p["aiStats"]["review"]["rejected"] == {"bad_sentence_id": 2} and p["aiReviewCount"] == 3
    items = (await client.get(f"/v1/lesson-plans/{p['id']}/ai-items")).json()["items"]
    assert all(len(i["sourceQuote"]) >= 15 and "[S" not in i["sourceQuote"] for i in items)  # a real plan sentence, written by the server
    assert all(i["sourceQuote"] == i["payload"]["source_quote"] for i in items)


async def test_the_gap_between_quiz_and_review_calls_is_respected(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    order: list[str] = []

    class Recorder:
        async def complete(self, system: str, user: str, max_tokens: int, timeout: float | None = None) -> tuple[str, int, int]:
            order.append("review" if system == quizgen.SYSTEM_REVIEW else "quiz")
            return await quizgen.MockQuizLLM().complete(system, user, max_tokens)

    async def fake_sleep(s: float) -> None:
        order.append(f"sleep {s:g}")

    gen.setenv("QUIZ_GEN_MOCK", "false")
    gen.setenv("QUIZ_GEN_GAP_S", "20")
    get_settings.cache_clear()
    gen.setattr(quizgen, "get_client", lambda: Recorder())
    gen.setattr(quizgen.asyncio, "sleep", fake_sleep)
    await login(client, "gv.dia@preclass.local")
    await upload(client)
    assert order == ["quiz", "sleep 20", "review"]


async def test_val11_also_blocks_an_ai_question_whose_explanation_uses_data_the_stem_does_not_show(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    url = f"/v1/lesson-plans/{p['id']}/ai-items"
    for q in [x for x in (await client.get(url)).json()["items"] if x["kind"] == "quiz"]:
        assert (await client.patch(f"{url}/{q['id']}", json={"status": "approved"}, headers=H)).status_code == 200
    out = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()
    rev = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()["currentRevision"]["id"]
    blocks = (await client.get(f"/v1/revisions/{rev}/blocks")).json()["items"]
    def shown(it: dict[str, Any]) -> str:
        return json.dumps([it["payload"], *(b["payload"] for b in blocks if b["parentId"] == it["id"] and b["kind"] == "option")])

    # an AI question that leaves one plan figure out of its stem and options
    item, hidden = next((it, n) for it in blocks if it["kind"] == "worksheet_item" and it["payload"].get("hints")
                        for n in ("98,5", "1 091") if n not in shown(it))
    expl = next(b for b in blocks if b["kind"] == "explanation" and b["parentId"] == item["id"])
    edited = {**expl["payload"], "text": expl["payload"]["text"] + f" Số liệu của giáo án: {hidden}."}
    assert (await client.patch(f"/v1/blocks/{expl['id']}", json={"payload": edited, "version": expl["version"]})).status_code == 200
    res = (await client.post(f"/v1/revisions/{rev}/validate")).json()
    failed = [v for b in res["blocks"] for v in b.get("failedRules", []) if b["blockId"] in (item["id"], expl["id"])]
    assert "VAL-11" in failed, res


async def test_the_wait_between_provider_calls_does_not_block_the_server(client: httpx.AsyncClient, gen: pytest.MonkeyPatch) -> None:
    gen.setenv("QUIZ_GEN_GAP_S", "2")  # asyncio.sleep inside the job: the event loop stays free
    get_settings.cache_clear()
    await login(client, "gv.dia@preclass.local")
    r = await client.post("/v1/lesson-plans", files={"file": ("plan.docx", plan_docx(knowledge=KNOW))}, headers=H)
    assert r.status_code == 202
    t0 = time.monotonic()
    assert (await client.get("/v1/health")).status_code == 200
    assert time.monotonic() - t0 < 1
    for _ in range(60):  # let the job finish so it does not leak into the next test
        if (await client.get(f"/v1/lesson-plans/jobs/{r.json()['id']}")).json()["state"] == "done":
            break
        await asyncio.sleep(0.5)


# ---- the teacher chooses the parts, the counts and the level
async def test_the_teacher_chooses_counts_and_level_and_numeric_answers_are_recomputed(
    client: httpx.AsyncClient, db: AsyncSession, gen: pytest.MonkeyPatch
) -> None:
    await login(client, "gv.dia@preclass.local")
    p = await upload(client)
    url = f"/v1/lesson-plans/{p['id']}/ai-items"
    started: list[tuple[object, quizgen.QuizSpec | None]] = []
    gen.setattr(quizgen, "start", lambda pid, spec=None: started.append((pid, spec)))
    too_many = await client.post(f"{url}/regenerate", json={"mcq": 6, "numeric": 3}, headers=H)
    assert too_many.status_code == 422 and too_many.json()["code"] == "QUIZ_COUNT"  # more than QUIZ_GEN_PER_LESSON (8) in total
    assert not started
    ok = await client.post(f"{url}/regenerate", json={"mcq": 3, "numeric": 1, "level": "VAN_DUNG"}, headers=H)
    assert ok.status_code == 202 and started[0][1] == quizgen.QuizSpec(3, 1, "VAN_DUNG")
    await quizgen.run_plan(db, UUID(p["id"]), spec=started[0][1])
    quiz = [i for i in (await client.get(url)).json()["items"] if i["kind"] == "quiz"]
    mcq = [i for i in quiz if i["payload"]["item_type"] == "MCQ"]
    numeric = [i for i in quiz if i["payload"]["item_type"] == "NUMERIC"]
    assert len(mcq) == 3 and len(numeric) == 1
    assert {i["payload"]["level"] for i in quiz} == {"VAN_DUNG"}  # the label is on every question
    n = numeric[0]["payload"]
    assert n["op"] == "diff" and n["answer"] == pytest.approx(n["operands"][0] - n["operands"][1])  # the server's own result
    assert numeric[0]["status"] == "draft" and numeric[0]["needsConfirmation"]

    bad = await client.patch(f"{url}/{numeric[0]['id']}", json={"payload": {**n, "answer": n["answer"] + 5}}, headers=H)
    assert bad.status_code == 422  # an edit that breaks the sum is refused
    edited = await client.patch(f"{url}/{numeric[0]['id']}", json={"payload": {**n, "level": "NHAN_BIET"}}, headers=H)
    assert edited.status_code == 200 and edited.json()["payload"]["level"] == "NHAN_BIET"  # the teacher can change the label
    assert (await client.patch(f"{url}/{numeric[0]['id']}", json={"status": "approved"}, headers=H)).status_code == 200

    out = (await client.post(f"/v1/lesson-plans/{p['id']}/lesson", headers=H)).json()
    rev = (await client.get(f"/v1/lessons/{out['lessonId']}")).json()["currentRevision"]["id"]
    blocks = (await client.get(f"/v1/revisions/{rev}/blocks")).json()["items"]
    item = next(b for b in blocks if b["kind"] == "worksheet_item" and b["payload"].get("itemType") == "NUMERIC")
    assert item["payload"]["level"] == "NHAN_BIET" and item["transformation"] == "AI_PROPOSED"
    key = next(b for b in blocks if b["kind"] == "answer_key" and b["parentId"] == item["id"])
    assert key["payload"]["value"] == pytest.approx(n["answer"]) and key["payload"]["derivation"]["op"] == "diff" and key["payload"]["unit"]
    for b in blocks:  # no blocker: the usual per-block approval works for the numeric item too
        if b["id"] in (item["id"], key["id"]):
            r = await client.post(f"/v1/blocks/{b['id']}/reviews", json={"action": "APPROVE", "contentHash": b["contentHash"]})
            ev = (await db.execute(text("SELECT rule, evidence FROM validation_result WHERE block_id=:i AND outcome='FAIL'"), {"i": b["id"]})).all()
            assert r.status_code == 201, (b["kind"], ev)
