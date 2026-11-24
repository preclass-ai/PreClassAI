"""Which lesson-plan lines a student may read on their own. No I/O; shared by the lesson builder and the student API."""

import re

from app.lessonplan.redact import fold
from app.lessonplan.structure import STEP, SUB

# Lines a student cannot use on their own: teacher-facing CV 5512 scaffolding ("a) Mục tiêu: ...", "Bước 1: GV ...")
# and in-class prompts that need a picture, video or game the pre-class lesson does not carry.
_TEACHER_SIDE = re.compile(r"\b(?:gv|giao vien)\b")
_IN_CLASS = re.compile(r"\b(?:tranh|hinh anh|video|clip|quan sat|tro choi|o chu|lat cac)\b")


def for_student(text: str) -> bool:
    """A mở đầu / vận dụng line a student can act on at home, alone (not lesson-plan scaffolding, not an in-class prompt)."""
    f = fold(text).lstrip("*-•+ ").strip()
    return not (SUB.match(f) or STEP.match(f) or _TEACHER_SIDE.search(f) or _IN_CLASS.search(f))


_PLAN_WORD = re.compile(r"\b(g|G)iáo án\b")


def student_text(s: str) -> str:
    """Students never see the teacher's plan: text citing it ("Theo giáo án, ...") cites the lesson instead. Applied when
    snapshot text is read, so lessons published before quizgen stopped writing "giáo án" read right too."""
    return _PLAN_WORD.sub(lambda m: "bài học" if m.group(1) == "g" else "Bài học", s)
