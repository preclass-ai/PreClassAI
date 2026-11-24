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
        "stem": "Dân số nước ta năm 2021 là bao nhiêu triệu người?", "options": ["98,5 triệu người", "Đứng thứ nhất Đông Nam Á", "Đứng thứ hai Đông Nam Á", "Không được nêu trong giáo án"],
        "correct_index": 0, "explanation": "Theo bài học, dân số năm 2021 là 98,5 triệu người.",
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
    assert check_question(q(options=["99 triệu người", "Đứng thứ hai", "Đứng thứ nhất", "Không nêu"]), SRC) == "number_not_in_plan"


def test_every_number_must_be_in_the_quoted_sentences_not_just_somewhere_in_the_plan() -> None:
    right = q(options=["1 091 người", "Đứng thứ hai Đông Nam Á", "Đứng thứ nhất Đông Nam Á", "Không nêu"])  # 1 091 is in S2, the quote is S1
    assert check_question(right, SRC) == "number_not_in_quote"  # the right answer's figure
    distractor = q(options=["98,5 triệu người", "1 091 người", "Đứng thứ nhất Đông Nam Á", "Không nêu"])
    assert check_question(distractor, SRC) == "number_not_in_quote"  # a distractor's figure
    stem = q(stem="Năm 2021 đồng bằng sông Hồng có mật độ 1 091 người trên km2, dân số nước ta là bao nhiêu?")
    assert check_question(stem, SRC) == "number_not_in_quote"
    both = q(source_sentence_ids=[1, 2], source_quote="", options=["98,5 triệu người", "1 091 người", "Đứng thứ nhất", "Không nêu"])
    assert check_question(both, SRC) is None  # the figure is fine once its sentence is cited


@pytest.mark.parametrize("stem", [
    "Trong hoạt động nhóm, học sinh cần sử dụng thiết bị nào để hoàn thành nhiệm vụ?",
    "Giáo viên yêu cầu các em nộp bài qua phần mềm nào sau đây?",
    "Mỗi nhóm học sinh cần chia sẻ sản phẩm lên ứng dụng nào?",
    "Theo phân công của giáo viên, nhóm trưởng ghi kết quả vào đâu?",
])
def test_questions_about_running_the_class_are_rejected(stem: str) -> None:
    assert check_question(q(stem=stem), SRC) == "procedural"


def test_a_geography_question_with_the_word_nhom_is_kept() -> None:
    assert check_question(q(stem="Nhóm tuổi nào chiếm tỉ trọng cao nhất trong cơ cấu dân số nước ta năm 2021?"), SRC) is None


def test_sentence_references_become_theo_giao_an() -> None:
    from app.lessonplan.quizgen import clean_refs

    assert clean_refs("Số liệu nằm ở mục [3] của bài.") == "Số liệu nằm theo bài học của bài."
    assert clean_refs("Theo [S2], dân số tăng.") == "Theo bài học, dân số tăng."
    assert clean_refs("[S4] nêu mật độ dân số.") == "Theo bài học nêu mật độ dân số."
    assert clean_refs("Đáp án đúng, xem [1, 2].") == "Đáp án đúng, theo bài học."
    assert clean_refs("Theo giáo án, môn Địa lí liên quan tới gì? Giáo án viết rõ.") == "Theo bài học, môn Địa lí liên quan tới gì? Bài học viết rõ."
    assert clean_refs("Không có tham chiếu nào.") == "Không có tham chiếu nào."
    d = q(explanation="Theo [S1] và mục [2], dân số là 98,5 triệu người.", hints=["Đọc [S1].", "Em xem mục [2] nhé.", "Chú ý đơn vị em nhé."])
    assert "[" not in d.explanation and all("[" not in h for h in d.hints)  # cleaned before the draft is stored
    c = card(points=["Năm 2021 có 98,5 triệu người [S1].", "Đứng thứ ba [S1]."], check={
        "statement": "Dân số nước ta năm 2021 là 98,5 triệu người.", "answer_true": True, "explanation": "Đúng, xem [S1]."})
    assert "[" not in " ".join(c.points) and "[" not in c.check.explanation


def _plan_sections() -> tuple[list[object], dict[object, object], list[tuple[str, str]]]:
    """A 5512 plan in miniature: (sections, anchors by id, what the model may see)."""
    from types import SimpleNamespace as NS
    from uuid import uuid4

    by: dict[object, object] = {}

    def sec(kind: str, sub: str | None, *items: tuple[str, str]) -> NS:
        ids = []
        for k, text in items:
            a = NS(id=uuid4(), kind=k, excerpt=text)
            by[a.id] = a
            ids.append(a.id)
        return NS(kind=kind, sub=sub, anchor_ids=ids)

    secs = [
        sec("objectives", None, ("HEADING", "1. Kiến thức"), ("PARAGRAPH", "Trình bày được đặc điểm phân bố dân cư của nước ta hiện nay."),
            ("PARAGRAPH", "2. Năng lực"), ("PARAGRAPH", "a) Năng lực chung: tự chủ và tự học thông qua nhiệm vụ cá nhân của lớp."),
            ("PARAGRAPH", "b) Năng lực số: sử dụng Padlet để chia sẻ sản phẩm học tập."), ("PARAGRAPH", "3. Phẩm chất: chăm chỉ, trách nhiệm với tập thể.")),
        sec("equipment", None, ("PARAGRAPH", "Thiết bị dạy học: máy chiếu, điện thoại, bảng phụ cho các nhóm.")),
        sec("activity", None, ("HEADING", "Hoạt động 2: Hình thành kiến thức"), ("PARAGRAPH", "Dân số nước ta năm 2021 là 98,5 triệu người, đứng thứ ba Đông Nam Á.")),
        sec("sub", "noi_dung", ("PARAGRAPH", "Em hãy nhận xét sự phân bố dân cư theo bảng số liệu dưới đây?"), ("TABLE_CELL", "Đồng bằng sông Hồng 1 091 người trên km2")),
        sec("sub", "san_pham", ("PARAGRAPH", "Sản phẩm: bài trình bày của các nhóm về phân bố dân cư nước ta.")),
        sec("sub", "to_chuc", ("PARAGRAPH", "Giáo viên chuyển giao nhiệm vụ và chia lớp thành 4 nhóm làm việc trên Zalo.")),
        sec("step", "to_chuc", ("PARAGRAPH", "Bước 1: Chuyển giao nhiệm vụ"), ("PARAGRAPH", "Giáo viên phân công các nhóm trưởng thu bài trên Padlet.")),
        sec("step", "to_chuc", ("PARAGRAPH", "Bước 4: Kết luận, nhận định"), ("PARAGRAPH", "Dân cư nước ta tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi.")),
    ]
    want = [
        ("muc_tieu", "Trình bày được đặc điểm phân bố dân cư của nước ta hiện nay."),
        ("noi_dung", "Dân số nước ta năm 2021 là 98,5 triệu người, đứng thứ ba Đông Nam Á."),
        ("cau_hoi", "Em hãy nhận xét sự phân bố dân cư theo bảng số liệu dưới đây?"),
        ("bang", "Đồng bằng sông Hồng 1 091 người trên km2"),
        ("ket_luan", "Dân cư nước ta tập trung đông ở đồng bằng và đô thị, thưa thớt ở miền núi."),
    ]
    return secs, by, want


def test_only_knowledge_content_reaches_the_model() -> None:
    secs, by, want = _plan_sections()
    assert quizgen.passages(secs, by, set()) == want  # no equipment, competencies, qualities, products, hand-over, group work, Padlet or Zalo


def test_a_tagged_sentence_keeps_its_kind() -> None:
    src = Source("Dân số nước ta năm 2021 là 98,5 triệu người, đứng thứ ba Đông Nam Á.\nEm hãy nhận xét sự phân bố dân cư theo bảng dưới đây?",
                 {"Dân số nước ta năm 2021 là 98,5 triệu người, đứng thứ ba Đông Nam Á.": "noi_dung",
                  "Em hãy nhận xét sự phân bố dân cư theo bảng dưới đây?": "cau_hoi"})
    assert src.kinds == ["noi_dung", "cau_hoi"]


def test_old_drafts_are_cleaned_for_display() -> None:
    from app.lessonplan.quizgen import clean_payload

    out = clean_payload("quiz", {"explanation": "Xem mục [4].", "hints": ["Đọc [S2].", "a", "b"]})
    assert out["explanation"] == "Theo bài học." and out["hints"][0] == "Đọc theo bài học."


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
    assert not hasattr(q(extra_field="x"), "extra_field")  # an extra key is ignored, not a reason to drop the question
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

    async def fake_run_plan(db: object, plan_id: object, client: object = None, spec: object = None) -> dict[str, object]:
        log.append(f"start {plan_id}")
        await asyncio.sleep(0.02)
        log.append(f"end {plan_id}")
        return {}

    monkeypatch.setattr(quizgen, "run_plan", fake_run_plan)

    async def go() -> None:
        await asyncio.gather(*(quizgen.run_one(None, i) for i in (1, 2, 3)))  # type: ignore[arg-type]

    asyncio.run(go())
    assert log == ["start 1", "end 1", "start 2", "end 2", "start 3", "end 3"]  # never two at once


# ---- E2: a bad card does not cost the batch; a wholly bad reply is retried once with the field names
def test_one_bad_card_keeps_the_others_and_names_only_the_field() -> None:
    good = card().model_dump()
    no_check = {k: v for k, v in good.items() if k != "check"}
    five_points = {**good, "points": ["một ý đủ dài"] * 5}
    fields: set[str] = set()
    ok, bad = parse_items(json.dumps({"cards": [good, no_check, five_points]}), "cards", AiCard, fields)
    assert len(ok) == 2 and bad == 1 and fields == {"check"}


def test_all_bad_reply_is_retried_once_with_field_names() -> None:
    seen: list[str] = []
    good = json.dumps({"questions": [q().model_dump()]})

    class Bad:
        async def complete(self, system: str, user: str, max_tokens: int, timeout: float | None = None) -> tuple[str, int, int]:
            seen.append(user)
            return (json.dumps({"questions": [{"stem": "thiếu trường nhiều"}]}) if len(seen) == 1 else good), 10, 10

    ok, bad, *_ = asyncio.run(quizgen._ask(Bad(), quizgen.SYSTEM_QUIZ, PLAN, "Soạn cần 3", "questions", AiQuestion, 100, 60.0))  # noqa: SLF001
    assert len(seen) == 2 and "sai ở trường" in seen[1] and "options" in seen[1] and len(ok) == 1


def test_quiz_client_uses_the_quiz_model_pair(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import get_settings
    for k, v in (("CHAT_LLM_BASE_URL", "https://api.groq.com/openai/v1"), ("CHAT_LLM_API_KEY", "k"), ("CHAT_LLM_MODEL", "chat-m")):
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    try:
        assert quizgen.get_client().models == ["openai/gpt-oss-120b", "qwen/qwen3.8-27b"]  # type: ignore[union-attr]
    finally:
        get_settings.cache_clear()


# ---- part III: numeric answers the server works out again
NUM_PLAN = Source("Năm 2021 dân số vùng Đồng bằng sông Hồng là 23,2 triệu người, vùng Trung du và miền núi phía Bắc là 12,9 triệu người trong cả nước.")


def num(**kw: object) -> quizgen.AiNumeric:
    base: dict[str, object] = {
        "stem": "Dân số vùng Đồng bằng sông Hồng là 23,2 triệu người, vùng Trung du và miền núi phía Bắc là 12,9 triệu người. Tính chênh lệch.",
        "op": "diff", "operands": [23.2, 12.9], "unit": "triệu người", "answer": 10.3, "explanation": "Lấy 23,2 trừ 12,9 được 10,3 triệu người.",
        "hints": ["Em tìm hai số cần dùng.", "Em chọn phép trừ.", "Em chú ý đơn vị."], "source_sentence_ids": [1]}
    return quizgen.AiNumeric.model_validate({**base, **kw})


def test_a_numeric_answer_that_follows_from_the_quote_passes() -> None:
    d = num()
    assert check_question_numeric(d) is None and d.answer == 10.3


def check_question_numeric(d: quizgen.AiNumeric) -> str | None:
    return quizgen.check_numeric(d, NUM_PLAN)


def test_a_wrong_numeric_answer_is_rejected_even_when_the_figures_are_in_the_quote() -> None:
    assert check_question_numeric(num(answer=11.3)) == "answer_mismatch"
    assert check_question_numeric(num(op="sum", answer=10.3)) == "answer_mismatch"
    assert not quizgen.numeric_math_ok(num(op="ratio", operands=[23.2, 0], answer=0))  # division by zero cannot be recomputed


def test_numeric_operands_and_stem_figures_must_be_in_the_quote() -> None:
    assert check_question_numeric(num(operands=[23.2, 14.9], answer=8.3)) == "number_not_in_quote"
    assert check_question_numeric(num(stem="Dân số là 23,2 triệu người ở vùng này và 99 triệu người ở vùng kia. Tính chênh lệch.")) == "number_not_in_quote"


def test_a_numeric_hint_must_not_give_the_answer() -> None:
    assert check_question_numeric(num(hints=["Em tìm hai số.", "Kết quả là 10,3 em nhé.", "Em chú ý đơn vị."])) == "hint_leaks_answer"


def test_the_stored_numeric_answer_is_the_servers_result() -> None:
    d = num(operands=[23.2, 12.9], answer=10.31)  # within tolerance: the model rounded badly
    assert check_question_numeric(d) is None and d.answer == 10.3
    assert quizgen.numeric_math_ok(num()) and not quizgen.numeric_math_ok(num(answer=50))


def test_mock_numeric_output_passes_the_validator() -> None:
    raw, _, _ = asyncio.run(MockQuizLLM().complete(quizgen.SYSTEM_NUMERIC, f"<plan>\n{quizgen.numbered(NUM_PLAN)}\n</plan>\nSoạn cần 2 câu hỏi", 100))
    ok, bad = parse_items(raw, "numeric", quizgen.AiNumeric)
    assert ok and bad == 0 and all(quizgen.check_numeric(x, NUM_PLAN) is None for x in ok)  # type: ignore[arg-type]
