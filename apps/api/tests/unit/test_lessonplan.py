"""CV 5512 reader on synthetic plans: watermark, header, signature, activities, knowledge box, MCQ answer from underline."""

from datetime import date

import pytest

from app.lessonplan import parse_plan_file
from app.lessonplan.model import PlanFile
from app.lessonplan.structure import _parse_mcq, _Unit
from tests.plan_fixtures import font_path, plan_docx, plan_pdf

FONT = font_path()
needs_font = pytest.mark.skipif(FONT is None, reason="no TrueType font with Vietnamese glyphs on this machine")
ALL4 = {"mo_dau", "hinh_thanh", "luyen_tap", "van_dung"}


def texts(plan: PlanFile) -> str:
    return "\n".join(a.excerpt for a in plan.anchors)


@pytest.fixture(scope="module", params=["line", "rect"])
def pdf_plan(request: pytest.FixtureRequest) -> PlanFile:
    assert FONT
    return parse_plan_file(plan_pdf(FONT, underline=request.param))


@needs_font
def test_two_lessons_in_one_file_with_metadata(pdf_plan: PlanFile) -> None:
    a, b = pdf_plan.lessons
    assert (a.title, a.ppct_period, a.week, a.subject, a.grade) == ("DÂN CƯ MẪU", "5", "3", "DIA_LI", 10)
    assert a.planned_on == date(2026, 9, 1) and a.taught_from == a.taught_to == date(2026, 9, 8)
    assert (b.title, b.ppct_period) == ("ĐÔ THỊ MẪU", "6")
    assert (b.taught_from, b.taught_to) == (date(2026, 9, 15), date(2026, 9, 16))


@needs_font
def test_four_activities_found_in_both_title_styles(pdf_plan: PlanFile) -> None:
    assert all(lesson.activities == ALL4 for lesson in pdf_plan.lessons)  # "HOẠT ĐỘNG 1: MỞ ĐẦU" and "Hoạt động 1. Khởi động"


@needs_font
def test_watermark_header_footer_never_become_anchors(pdf_plan: PlanFile) -> None:
    t = texts(pdf_plan)
    assert "BAN HÀNH" not in t and "TÀI LIỆU" not in t  # rotated grey watermark
    assert "TRƯỜNG THPT MẪU" not in t and "Trang 1" not in t  # repeated header and footer


@needs_font
def test_signature_and_teacher_names_are_redacted(pdf_plan: PlanFile) -> None:
    t = texts(pdf_plan)
    for name in ("Nguyễn Văn Mẫu", "Trần Thị Thử", "Lê Văn Giả", "TỔ TRƯỞNG", "GIÁO VIÊN"):
        assert name not in t, name
    assert sum(lesson.redacted for lesson in pdf_plan.lessons) >= 4
    assert "Bước 1: GV chuyển giao" in t  # "GV" inside real content stays


@needs_font
def test_objectives_carry_a_competency_code(pdf_plan: PlanFile) -> None:
    codes = {o.competency_code for o in pdf_plan.lessons[0].objectives}
    assert {"NHAN_THUC", "TIM_HIEU"} <= codes


@needs_font
def test_knowledge_box_table_and_figure_are_typed(pdf_plan: PlanFile) -> None:
    types = {a.anchor_type for a in pdf_plan.anchors}
    assert {"knowledge_box", "table_cell", "figure_caption"} <= types
    box = next(a for a in pdf_plan.anchors if a.anchor_type == "knowledge_box")
    assert "100 triệu" in box.excerpt and "1,2%" in box.excerpt  # the two framed lines are one anchor


@needs_font
def test_mcq_answer_comes_from_the_underline(pdf_plan: PlanFile) -> None:
    q = pdf_plan.lessons[0].mcqs
    assert [(m.correct, m.answer_source, m.needs_confirmation) for m in q] == [
        ("B", "underline", False),  # options on separate lines, one underlined
        ("C", "underline", False),  # all options on one line
        (None, None, True),  # no underline: the teacher must confirm
        (None, None, True),  # two underlines: ambiguous, the teacher must confirm
    ]
    assert all(m.confidence == ("low" if m.needs_confirmation else "high") for m in q)
    assert len(q[0].options) == 4 and pdf_plan.anchors[q[0].stem].excerpt == "Vùng nào có dân số cao nhất?"
    assert pdf_plan.lessons[1].mcqs[1].correct == "D" and pdf_plan.lessons[1].mcqs[0].needs_confirmation  # two options only


@needs_font
def test_without_a_watermark_nothing_changes() -> None:
    assert FONT
    plan = parse_plan_file(plan_pdf(FONT, watermark=False))
    assert len(plan.lessons) == 2 and plan.lessons[0].activities == ALL4


def test_docx_underlined_run_is_the_answer() -> None:
    plan = parse_plan_file(plan_docx())
    (lesson,) = plan.lessons
    assert lesson.activities == ALL4 and lesson.subject == "DIA_LI" and lesson.taught_from == date(2026, 9, 22)
    assert [(m.correct, m.answer_source, m.needs_confirmation) for m in lesson.mcqs] == [("B", "docx_underline", False), (None, None, True)]
    assert "Phạm Văn Thử" not in texts(plan) and lesson.redacted >= 1


def test_another_subject_parses_the_same_way() -> None:
    plan = parse_plan_file(plan_docx(subject="LỊCH SỬ", grade=11))
    (lesson,) = plan.lessons
    assert lesson.subject == "LICH_SU" and lesson.grade == 11 and lesson.activities == ALL4
    assert all(o.competency_code is None for o in lesson.objectives)  # no catalogue for this subject yet: never guessed


def test_open_question_is_not_an_mcq() -> None:
    from app.lessonplan.model import Line

    assert _parse_mcq(_Unit("mcq", [Line("Câu 1. Em hãy nêu ví dụ về đô thị.", 1)])) is None


def test_the_last_option_stops_where_the_next_section_starts() -> None:
    from app.lessonplan.model import Line

    text = ("Câu 4. Vì sao nước ta thu hút đầu tư nước ngoài? A. Thị trường lớn. B. Vị trí thuận lợi. C. Chính trị ổn định. "
            "D. Nguồn lao động giá rẻ. c) Sản phẩm: Học sinh hoàn thành phiếu học tập. d) Tổ chức thực hiện: Bước 1: Chuyển giao nhiệm vụ.")
    parsed = _parse_mcq(_Unit("mcq", [Line(text, 1)]))
    assert parsed is not None
    stem, opts, _ = parsed
    assert stem == "Vì sao nước ta thu hút đầu tư nước ngoài?"
    assert [t for _, t in opts] == ["Thị trường lớn.", "Vị trí thuận lợi.", "Chính trị ổn định.", "Nguồn lao động giá rẻ."]
    for tail in ("Hoạt động 3: Luyện tập", "Bước 2: Thực hiện", "a) Mục tiêu: nêu được"):  # other section starts also end it
        got = _parse_mcq(_Unit("mcq", [Line(f"Câu 1. Hỏi gì? A. một B. hai C. ba D. bốn. {tail}", 1)]))
        assert got is not None and got[1][3][1] == "bốn."
    plain = _parse_mcq(_Unit("mcq", [Line("Câu 2. Hỏi gì? A. một B. hai C. ba D. bốn sản phẩm nông nghiệp", 1)]))
    assert plain is not None and plain[1][3][1] == "bốn sản phẩm nông nghiệp"  # a lower-case word inside an option is not a boundary


def test_a_file_that_is_not_a_plan_format_is_refused() -> None:
    from app.errors import ApiError

    with pytest.raises(ApiError):
        parse_plan_file(b"not a document")


async def test_model_labels_only_known_ids_and_labels() -> None:
    import json

    from app.lessonplan.label import label_missing
    from app.lessonplan.model import LessonDoc, PAnchor, Section

    plan = PlanFile(anchors=[PAnchor("HEADING", "heading", {}, "Khởi động"), PAnchor("HEADING", "heading", {}, "Ôn lại")])
    plan.lessons = [LessonDoc(sections=[Section("activity", "hinh_thanh", anchors=[0, 1])])]

    async def fake(system: str, user: str) -> str:
        assert "<data>" in user
        return json.dumps({"0": "mo_dau", "1": "hinh_thanh", "99": "van_dung", "x": "luyen_tap"})  # unknown id/label are ignored

    assert await label_missing(plan, 0, fake) == 1
    assert plan.lessons[0].activities == {"hinh_thanh", "mo_dau"}

    async def broken(system: str, user: str) -> str:
        return "not json"

    assert await label_missing(plan, 0, broken) == 0


async def test_parse_runs_in_the_isolated_child_process() -> None:
    from app.sources.formats import Limits, parse_isolated

    plan = await parse_isolated("plan", plan_docx(), Limits(timeout_s=60))
    assert isinstance(plan, PlanFile) and plan.lessons[0].activities == ALL4


def test_grade_12_plan_is_read_from_the_subject_line() -> None:
    (lesson,) = parse_plan_file(plan_docx(grade=12)).lessons
    assert lesson.subject == "DIA_LI" and lesson.grade == 12


def test_only_student_usable_lines_open_or_close_the_pre_class_lesson() -> None:
    from app.lessonplan.audience import for_student as ok

    assert not ok("a) Mục tiêu: Vận dụng tri thức địa lí giải quyết vấn đề thực tiễn.")
    assert not ok("b) Nội dung: Quan sát hình ảnh và trả lời câu hỏi.")
    assert not ok("Bước 1: GV chuyển giao nhiệm vụ cho cả lớp.")
    assert not ok("* Câu hỏi: Lật các số và cho biết tên nghề nghiệp được thể hiện qua bức tranh?")
    assert ok("Em có sống ở đô thị không?")
    assert ok("Em hãy vẽ biểu đồ dân số của địa phương mình.")


def test_published_text_cites_the_lesson_not_the_plan() -> None:
    from app.lessonplan.audience import student_text

    assert student_text("Theo giáo án, môn Địa lí giúp học sinh:") == "Theo bài học, môn Địa lí giúp học sinh:"
    assert student_text("Em đọc lại phần giáo án. Giáo án viết rõ.") == "Em đọc lại phần bài học. Bài học viết rõ."


def test_teacher_only_instruction_of_a_plan_lesson_is_not_shown() -> None:
    from app.student import _shown

    def blk(text: str) -> dict:
        return {"kind": "instruction", "payload": {"text": text}}

    assert not _shown(blk("a) Mục tiêu:Vận dụng tri thức địa lí giải quyết vấn đề thực tiễn."), True)
    assert not _shown(blk("* Câu hỏi: Lật các số và cho biết tên nghề nghiệp được thể hiện qua bức tranh?"), True)
    assert _shown(blk("Em hãy vẽ biểu đồ dân số của địa phương mình."), True)
    assert _shown(blk("Quan sát bảng số liệu và trả lời."), False)  # a lesson not built from a plan is left as the teacher wrote it
