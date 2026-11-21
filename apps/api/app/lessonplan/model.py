"""Plain data shapes shared by the PDF/DOCX readers and the 5512 structure parser (picklable, no I/O)."""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

AnchorType = Literal["paragraph", "heading", "knowledge_box", "table_cell", "figure_caption"]


@dataclass
class Line:
    """One visual line (PDF) or one paragraph / table cell (DOCX), already stripped of watermark text."""

    text: str
    page: int
    x0: float = 0.0
    top: float = 0.0
    bottom: float = 0.0
    boxed: bool = False  # inside a framed box: a knowledge box
    table: bool = False  # inside a table
    header: bool = False  # repeated header/footer: metadata source only, never an anchor
    wrap_ok: bool = True  # False for DOCX: a paragraph is never a wrapped continuation
    opts: dict[str, bool] = field(default_factory=dict)  # option letter A-D -> underlined


@dataclass
class PAnchor:
    kind: str  # an existing source_anchor kind: HEADING | PARAGRAPH | TABLE_CELL
    anchor_type: AnchorType
    locator: dict[str, int | str]
    excerpt: str


@dataclass
class Section:
    kind: str  # objectives | equipment | process | activity | sub | step
    activity_type: str | None = None  # mo_dau | hinh_thanh | luyen_tap | van_dung
    sub: str | None = None  # muc_tieu | noi_dung | san_pham | to_chuc
    anchors: list[int] = field(default_factory=list)  # indexes into PlanFile.anchors


@dataclass
class Objective:
    text: str
    competency_code: str | None
    anchor: int


@dataclass
class Mcq:
    stem: int  # anchor index
    options: list[int]  # anchor indexes in A..D order
    correct: str | None
    answer_source: str | None  # underline | docx_underline
    needs_confirmation: bool

    @property
    def confidence(self) -> str:
        return "low" if self.needs_confirmation else "high"


@dataclass
class LessonDoc:
    subject: str | None = None
    grade: int | None = None
    title: str = ""
    ppct_period: str | None = None
    week: str | None = None
    planned_on: date | None = None
    taught_from: date | None = None
    taught_to: date | None = None
    sections: list[Section] = field(default_factory=list)
    objectives: list[Objective] = field(default_factory=list)
    mcqs: list[Mcq] = field(default_factory=list)
    redacted: int = 0

    @property
    def activities(self) -> set[str]:
        return {s.activity_type for s in self.sections if s.kind == "activity" and s.activity_type}


@dataclass
class PlanFile:
    anchors: list[PAnchor] = field(default_factory=list)
    lessons: list[LessonDoc] = field(default_factory=list)
    pages: int = 0
