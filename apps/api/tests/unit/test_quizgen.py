"""Validators for AI-drafted questions and review cards: fake quotes, foreign numbers, duplicate options, leaking hints."""

import asyncio
import json

import pytest

from app.lessonplan import quizgen
from app.lessonplan.quizgen import AiCard, AiQuestion, MockQuizLLM, Source, check_card, check_question, parse_items

PLAN = (
    "Dân số nước ta năm 2021 là 98,5 triệu người, đứng thứ ba Đông Nam Á. "
    "Đồng bằng sông Hồng có mật độ dân số cao nhất cả nước, khoảng 1 091 người trên km2. "
    "Dân cư tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi do điều kiện tự nhiên và lịch sử khai thác lãnh thổ. "
    "Tỉ lệ dân thành thị tăng nhanh nhờ quá trình công nghiệp hóa và đô thị hóa diễn ra mạnh mẽ."
)
SRC = Source(PLAN)


def q(**kw: object) -> AiQuestion:
    base: dict[str, object] = {
        "stem": "Dân số nước ta năm 2021 là bao nhiêu triệu người?", "options": ["98,5 triệu người", "90 triệu người", "80 triệu người", "70 triệu người"],
        "correct_index": 0, "explanation": "Theo giáo án, dân số năm 2021 là 98,5 triệu người.",
        "hints": ["Em đọc lại phần dân số trong bài.", "Em tìm con số gắn với năm đề hỏi.", "Em chú ý đơn vị là triệu người."],
        "skill_tag": "READ_TABLE", "source_quote": "Dân số nước ta năm 2021 là 98,5 triệu người, đứng thứ ba Đông Nam Á."}
    return AiQuestion.model_validate({**base, **kw})


def test_a_good_question_passes() -> None:
    assert check_question(q(), SRC) is None


def test_fake_quote_is_rejected() -> None:
    assert check_question(q(source_quote="Việt Nam có dân số đông nhất châu Á và đang giảm mạnh mỗi năm."), SRC) == "quote_not_in_plan"
    assert check_question(q(source_quote="dân số nước ta năm 2021 là 98,5 triệu người đứng thứ ba đông nam á"), SRC) is None  # case and accents do not matter


def test_number_that_is_not_in_the_plan_is_rejected() -> None:
    assert check_question(q(stem="Dân số nước ta năm 2021 là bao nhiêu triệu người, so với 120 triệu?"), SRC) == "number_not_in_plan"
    assert check_question(q(options=["99 triệu người", "90 triệu người", "80 triệu người", "70 triệu người"]), SRC) == "number_not_in_plan"


def test_duplicate_options_are_rejected() -> None:
    assert check_question(q(options=["98,5 triệu người", "98,5 triệu người", "80 triệu người", "70 triệu người"]), SRC) == "options_duplicate"
    assert check_question(q(options=["98,5 triệu người", "98,5 Triệu Người.", "80 triệu người", "70 triệu người"]), SRC) == "options_duplicate"


def test_hint_that_gives_the_answer_is_rejected() -> None:
    leak = q(hints=["Em đọc lại phần dân số.", "Đáp án là A.", "Em chú ý đơn vị."])
    assert check_question(leak, SRC) == "hint_leaks_answer"
    assert check_question(q(hints=["Em đọc lại phần dân số.", "Con số là 98,5 triệu người đó em.", "Em chú ý đơn vị."]), SRC) == "hint_leaks_answer"


def test_schema_is_strict() -> None:
    with pytest.raises(ValueError):
        q(options=["a", "b", "c"])  # not four
    with pytest.raises(ValueError):
        q(correct_index=4)
    with pytest.raises(ValueError):
        q(hints=["một", "hai"])
    with pytest.raises(ValueError):
        q(extra_field="x")
    with pytest.raises(ValueError):
        q(skill_tag="GUESS")


def card(**kw: object) -> AiCard:
    base: dict[str, object] = {
        "title": "Dân số nước ta", "points": ["Năm 2021 có 98,5 triệu người.", "Đứng thứ ba Đông Nam Á."],
        "example": "Đồng bằng sông Hồng khoảng 1 091 người trên km2.", "source_quote": "Dân số nước ta năm 2021 là 98,5 triệu người, đứng thứ ba Đông Nam Á.",
        "check": {"statement": "Dân số nước ta năm 2021 là 98,5 triệu người.", "answer_true": True, "explanation": "Đúng, giáo án nêu 98,5 triệu người."}}
    return AiCard.model_validate({**base, **kw})


def test_review_card_validator() -> None:
    assert check_card(card(), SRC) is None
    assert check_card(card(source_quote="Một câu hoàn toàn không có trong giáo án của tiết học này."), SRC) == "quote_not_in_plan"
    assert check_card(card(points=["Năm 2021 có 120 triệu người.", "Đứng thứ ba."]), SRC) == "number_not_in_plan"
    with pytest.raises(ValueError):
        card(points=["chỉ một ý"])


def test_parse_items_keeps_valid_and_counts_schema_failures() -> None:
    raw = "```json\n" + json.dumps({"questions": [q().model_dump(), {"stem": "thiếu trường"}]}, ensure_ascii=False) + "\n```"
    ok, bad = parse_items(raw, "questions", AiQuestion)
    assert len(ok) == 1 and bad == 1
    with pytest.raises(ValueError):
        parse_items("không phải JSON", "questions", AiQuestion)


def test_mock_model_output_passes_the_validators() -> None:
    src = Source(PLAN)
    raw, _, _ = asyncio.run(MockQuizLLM().complete(quizgen.SYSTEM_QUIZ, f"<plan>\n{quizgen.numbered(src)}\n</plan>\nSoạn cần 3 câu hỏi", 100))
    ok, bad = parse_items(raw, "questions", AiQuestion)
    assert ok and bad == 0 and all(check_question(x, src) is None for x in ok)  # type: ignore[arg-type]


# ---- quote matching: both sides are folded the same way
import unicodedata  # noqa: E402

from app.generation.providers import ProviderHTTPError, clean_error_body  # noqa: E402
from app.lessonplan.quizgen import FUZZY_MIN, fold, quote_score  # noqa: E402

LONG = "Dân cư tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi do điều kiện tự nhiên và lịch sử khai thác lãnh thổ."


def test_nfc_and_nfd_spellings_match() -> None:
    nfd = unicodedata.normalize("NFD", LONG)
    assert nfd != LONG and quote_score(nfd, SRC) == 100
    assert fold(nfd) == fold(LONG)


def test_line_breaks_and_pdf_hyphens_do_not_matter() -> None:
    broken = "Dân cư tập trung đông ở đồng bằng và đô\nthị, thưa thớt ở miền núi do điều kiện tự\n  nhiên và lịch sử khai thác lãnh thổ."
    hyphen = "Dân cư tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi do điều kiện tự nhiên và lịch sử khai thác lãnh-\nthổ."
    soft = "Dân cư tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi do điều kiện tự nhiên và lịch sử khai thác lãn­h thổ."
    spaced = "Dân cư tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi do điều kiện tự nhiên và lịch sử khai thác lãnh- thổ."
    for q in (broken, soft, spaced, LONG.upper()):
        assert quote_score(q, SRC) == 100, q
    assert quote_score(hyphen, SRC) == 100
    wrapped = Source("Dân cư tập trung đông ở đồng bằng và đô-\nthị, thưa thớt ở miền núi do điều kiện tự nhiên.")  # the PLAN is hyphen-wrapped
    assert quote_score("Dân cư tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi do điều kiện tự nhiên.", wrapped) == 100


def test_fuzzy_match_accepts_small_slips_and_rejects_a_rewrite() -> None:
    slip = LONG.replace("thưa thớt", "thưa thớt hơn").replace("lãnh thổ", "lãnh thổ nước ta")
    assert FUZZY_MIN <= quote_score(slip, SRC) < 100 and quizgen.quote_ok(slip, SRC)
    rewrite = "Người dân sống chủ yếu ở vùng đồng bằng vì có nhiều thuận lợi hơn miền núi về giao thông và việc làm."
    assert quote_score(rewrite, SRC) < FUZZY_MIN and not quizgen.quote_ok(rewrite, SRC)
    short = "dân số nước ta 98,5 tr"  # under 30 characters: must be exact
    assert len(fold(short)) < 30 and not quizgen.quote_ok(short, SRC)


# ---- provider errors and the retry
def test_error_body_keeps_status_text_short_and_hides_the_model_output() -> None:
    body = '{"error":{"message":"Rate limit reached. Please try again in 7.5s","type":"tokens","code":"rate_limit_exceeded","failed_generation":"NỘI DUNG GIÁO ÁN"}}'.encode()
    out = clean_error_body(body, "KEY123")
    assert "rate_limit_exceeded" in out and "7.5s" in out and "NỘI DUNG GIÁO ÁN" not in out and len(out) <= 200
    assert len(clean_error_body(b"x" * 5000 + b"KEY123", "KEY123")) == 200
    assert "KEY123" not in clean_error_body(b"oops KEY123", "KEY123")


class Flaky:
    def __init__(self, *errors: BaseException) -> None:
        self.errors, self.calls = list(errors), 0

    async def complete(self, system: str, user: str, max_tokens: int, timeout: float | None = None) -> tuple[str, int, int]:
        self.calls += 1
        if self.errors:
            raise self.errors.pop(0)
        return await MockQuizLLM().complete(system, user, max_tokens)


def _ask_with(client: Flaky) -> object:
    return asyncio.run(quizgen._ask(client, quizgen.SYSTEM_QUIZ, PLAN, "Soạn cần 3 câu hỏi", "questions", AiQuestion, 100, 60.0))  # noqa: SLF001


def test_429_is_retried_once_after_the_wait_the_provider_asked_for(monkeypatch: pytest.MonkeyPatch) -> None:
    waits: list[float] = []

    async def fake_sleep(s: float) -> None:
        waits.append(s)

    monkeypatch.setattr(quizgen.asyncio, "sleep", fake_sleep)
    c = Flaky(ProviderHTTPError(429, "rate_limit_exceeded Please try again in 1m2.5s"))
    _ask_with(c)
    assert c.calls == 2 and waits == [30.0]  # 62.5 s asked, capped
    c = Flaky(ProviderHTTPError(503, "down"))
    _ask_with(c)
    assert c.calls == 2 and waits[-1] == 12.0
    with pytest.raises(ProviderHTTPError) as e:  # a second 429 is not retried again
        _ask_with(Flaky(ProviderHTTPError(429, "x"), ProviderHTTPError(429, "y")))
    assert e.value.status == 429


@pytest.mark.parametrize("err", [ProviderHTTPError(400, "json_validate_failed"), ProviderHTTPError(401, "bad key"), TimeoutError()])
def test_400_and_timeout_are_not_retried(err: BaseException) -> None:
    c = Flaky(err)
    with pytest.raises(type(err)):
        _ask_with(c)
    assert c.calls == 1


# ---- sentence ids: the server writes the quote
def test_sentences_are_numbered_and_short_pieces_dropped() -> None:
    src = Source("Mục tiêu\nDân số nước ta năm 2021 là 98,5 triệu người. Ok.\nĐồng bằng sông Hồng có mật độ dân số cao nhất cả nước!")
    assert src.sentences == ["Dân số nước ta năm 2021 là 98,5 triệu người.", "Đồng bằng sông Hồng có mật độ dân số cao nhất cả nước!"]
    assert quizgen.numbered(src).splitlines()[1].startswith("[S2] Đồng bằng")


def test_ids_become_the_verbatim_quote() -> None:
    d = q(source_sentence_ids=[2, 1, 2], source_quote="")
    assert check_question(d, SRC) is None
    assert d.source_quote == f"{SRC.sentences[0]} {SRC.sentences[1]}"  # sorted, de-duplicated, written by the server
    c = card(source_sentence_ids=[1], source_quote="")
    assert check_card(c, SRC) is None and c.source_quote == SRC.sentences[0]


def test_unknown_ids_are_rejected() -> None:
    assert check_question(q(source_sentence_ids=[99], source_quote=""), SRC) == "bad_sentence_id"
    assert check_question(q(source_sentence_ids=[0], source_quote=""), SRC) == "bad_sentence_id"
    assert check_card(card(source_sentence_ids=[1, 5], source_quote=""), SRC) == "bad_sentence_id"
    with pytest.raises(ValueError):
        q(source_sentence_ids=[1, 2, 3, 4], source_quote="")  # at most three
    with pytest.raises(ValueError):
        q(source_sentence_ids=[], source_quote="")  # neither ids nor a quote


def test_a_foreign_number_is_still_rejected_when_the_ids_are_fine() -> None:
    d = q(source_sentence_ids=[1], source_quote="", stem="Dân số nước ta năm 2021 là bao nhiêu triệu người, so với 120 triệu?")
    assert check_question(d, SRC) == "number_not_in_plan"


def test_text_instead_of_ids_falls_back_to_the_fuzzy_match_at_85() -> None:
    assert FUZZY_MIN == 85
    assert check_question(q(), SRC) is None  # the old path: a verbatim quote
    assert check_question(q(source_quote="Việt Nam có dân số đông nhất châu Á và đang giảm mạnh mỗi năm."), SRC) == "quote_not_in_plan"


def test_prompt_is_cut_to_the_budget_appendix_first_then_the_tail() -> None:
    body = [f"Câu kiến thức số {i} nói về dân cư và lao động của nước ta trong giai đoạn gần đây." for i in range(400)]
    rubric = "Rubric chấm điểm và phụ lục phiếu học tập dành cho giáo viên khi tổ chức hoạt động nhóm."
    sents = [*body[:200], rubric, *body[200:]]
    out = quizgen.fit(sents, "x" * 1200)
    assert out == sents[:0] + [s for s in out]  # a list of the same sentences
    assert rubric not in out and out[0] == body[0] and len(out) < len(body)  # appendix gone, tail cut
    assert quizgen.est_tokens("x" * 1200) + sum(quizgen.est_tokens(s) + 2 for s in out) <= quizgen.INPUT_BUDGET_TOKENS
    assert quizgen.fit(body[:20], "x" * 1200) == body[:20]  # under the budget: untouched


# ---- one drafting job at a time
def test_jobs_run_one_at_a_time_in_arrival_order(monkeypatch: pytest.MonkeyPatch) -> None:
    log: list[str] = []

    async def fake_run_plan(db: object, plan_id: object, client: object = None) -> dict[str, object]:
        log.append(f"start {plan_id}")
        await asyncio.sleep(0.02)
        log.append(f"end {plan_id}")
        return {}

    monkeypatch.setattr(quizgen, "run_plan", fake_run_plan)

    async def go() -> None:
        await asyncio.gather(*(quizgen.run_one(None, i) for i in (1, 2, 3)))  # type: ignore[arg-type]

    asyncio.run(go())
    assert log == ["start 1", "end 1", "start 2", "end 2", "start 3", "end 3"]  # never two at once
