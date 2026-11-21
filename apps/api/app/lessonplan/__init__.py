"""Lesson plan reader (CV 5512): PDF or DOCX -> lessons with anchors, objectives, 4 activities and MCQ.

The answer of a multiple-choice question comes from an underline or from the teacher, never from a model. The optional
model (LESSON_PLAN_LLM, off by default) only labels paragraphs the rules could not place, see `label.py`.
"""

from app.errors import ApiError
from app.lessonplan.model import PlanFile
from app.lessonplan.readers import read_docx, read_pdf
from app.lessonplan.structure import parse_plan
from app.sources.formats import Limits, detect_kind


def parse_plan_file(data: bytes, lim: Limits | None = None) -> PlanFile:
    lim = lim or Limits()
    kind = detect_kind(data)
    if kind == "pdf":
        lines, pages = read_pdf(data, lim.pdf_pages)
    elif kind == "docx":
        lines, pages = read_docx(data)
    else:
        raise ApiError(422, "UNSUPPORTED_FILE", "Giáo án cần là tệp DOCX hoặc PDF có chữ")
    return parse_plan(lines, pages)
