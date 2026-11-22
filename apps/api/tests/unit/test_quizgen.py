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
    raw, _, _ = asyncio.run(MockQuizLLM().complete(quizgen.SYSTEM_QUIZ, f"<plan>\n{PLAN}\n</plan>\nSoạn cần 3 câu hỏi", 100))
    ok, bad = parse_items(raw, "questions", AiQuestion)
    assert ok and bad == 0 and all(check_question(x, src) is None for x in ok)  # type: ignore[arg-type]
