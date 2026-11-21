# ruff: noqa: E501  (regex tables and Vietnamese cue lists read better on one line)
"""CV 5512 lesson plan structure from `Line`s: lessons, metadata, objectives, 4 activities, anchors and MCQ.

Pure functions, no I/O, no model. Rules are soft: accent-free lowercase text, numbering and label variants accepted.
Nothing here is specific to one subject except the small tables SUBJECTS and COMPETENCY_CUES (config, not logic).
"""

import re
from dataclasses import dataclass
from datetime import date

from app.lessonplan.model import AnchorType, LessonDoc, Line, Mcq, Objective, PAnchor, PlanFile, Section
from app.lessonplan.redact import fold, redact

MAX_EXCERPT = 1500
SUBJECTS = {  # key -> folded names; only names that carry a subject word (a bare "toan" appears in "toan cau")
    "DIA_LI": ("dia li", "dia ly"), "LICH_SU": ("lich su",), "TOAN": ("toan hoc", "mon toan"), "NGU_VAN": ("ngu van",),
    "VAT_LI": ("vat li", "vat ly"), "HOA_HOC": ("hoa hoc",), "SINH_HOC": ("sinh hoc",), "TIN_HOC": ("tin hoc",),
    "GDKT_PL": ("giao duc kinh te va phap luat",), "CONG_NGHE": ("cong nghe",), "TIENG_ANH": ("tieng anh", "ngoai ngu"),
}
COMPETENCY_CUES = {  # subject -> (folded cue in the objective text, code); other subjects add theirs here
    "DIA_LI": (("nhan thuc khoa hoc dia li", "NHAN_THUC"), ("tim hieu dia li", "TIM_HIEU"), ("van dung kien thuc", "VAN_DUNG")),
}
KNOWLEDGE_DEFAULT = {"DIA_LI": "NHAN_THUC"}  # objectives under "Kiến thức" with no cue of their own
ACTIVITY_NAMES = (("mo dau", "mo_dau"), ("khoi dong", "mo_dau"), ("hinh thanh", "hinh_thanh"), ("kham pha", "hinh_thanh"),
                  ("kien thuc moi", "hinh_thanh"), ("luyen tap", "luyen_tap"), ("van dung", "van_dung"), ("mo rong", "van_dung"))
BY_NUMBER = {1: "mo_dau", 2: "hinh_thanh", 3: "luyen_tap", 4: "van_dung"}

TIET = re.compile(r"^tiet\s*(?:ppct)?\s*[:.]?\s*\d")
BAI = re.compile(r"^(?:BÀI|Bài)\s*(\d+)\s*[:.\-–]?\s*(.*)$")
CAU = re.compile(r"^\s*C[âa]u\s*(\d+)\s*[.:)]\s*(.*)$", re.IGNORECASE)
PART_I = re.compile(r"^(?:i|1)\s*[.)]\s*muc tieu")
PART_II = re.compile(r"^(?:ii|2)\s*[.)]\s*(?:thiet bi|chuan bi)")
PART_III = re.compile(r"^(?:iii|3)\s*[.)]\s*(?:tien trinh|to chuc|hoat dong day hoc)")
ACTIVITY = re.compile(r"^(?:\d+\s*[.)]\s*)?hoat dong\s*(\d+)(?:\s*\.\s*(\d+))?\s*[:.\-]?\s*(.*)$")
SUB = re.compile(r"^(?:[a-d]\s*[.)]\s*)?(muc tieu|noi dung|san pham|to chuc thuc hien|to chuc)\b")
SUB_KIND = {"muc tieu": "muc_tieu", "noi dung": "noi_dung", "san pham": "san_pham", "to chuc thuc hien": "to_chuc", "to chuc": "to_chuc"}
STEP = re.compile(r"^buoc\s*[1-4]\b")
OBJ_HEAD = re.compile(r"^(?:\d+\s*[.)]\s*|[-•+*]\s*)?(kien thuc|nang luc chung|nang luc chuyen biet|nang luc dac thu|nang luc|pham chat)\s*[:.]?\s*$")
FIGURE = re.compile(r"^(?:hinh|bieu do|so do|luoc do|ban do|anh)\s*\d*\s*[.:]")
OPTION = re.compile(r"(?:(?<=\s)|^)([A-D])\s*[.)]\s*")
BULLET = re.compile(r"^\s*(?:[-•+*]|\d+\s*[.)]|[a-dA-D]\s*[.)]|buoc\s*\d|hoat dong|C[âa]u\s*\d)", re.IGNORECASE)
DATE = re.compile(r"(?<![\d/])(\d{1,2})\s*[/.\-]\s*(\d{1,2})(?:\s*[/.\-]\s*(\d{2,4}))?")
RANGE = re.compile(r"(?<![\d/])(\d{1,2})\s*[-–]\s*(\d{1,2})\s*/\s*(\d{1,2})(?:\s*/\s*(\d{2,4}))?")


# ---------------------------------------------------------------- lessons and metadata
def _head_start(ln: Line) -> bool:
    f = fold(ln.text)
    return not ln.header and bool(re.search(r"ngay soan", f) or TIET.match(f))


def split_lessons(lines: list[Line]) -> list[list[Line]]:
    """A lesson starts at its header block ("Ngày soạn", "Tiết PPCT"); without headers, at the first "BÀI n" of each number."""
    starts: list[int] = []
    for i, ln in enumerate(lines):
        if _head_start(ln) and (not starts or i - starts[-1] > 4):  # the lines of one header block are one start
            starts.append(i)
    if not starts:
        seen: set[str] = set()
        for i, ln in enumerate(lines):
            m = BAI.match(ln.text)
            if m and not ln.header and m.group(1) not in seen and ln.text.startswith("BÀI"):
                seen.add(m.group(1))
                starts.append(i)
    if not starts:
        return [lines] if lines else []
    for k, i in enumerate(starts):  # a "BÀI n" title printed just above its header belongs to this lesson
        if i - 2 >= 0 and k and any(BAI.match(lines[j].text) and lines[j].text.startswith("BÀI") for j in (i - 1, i - 2)):
            starts[k] = i - 2 if BAI.match(lines[i - 2].text) and lines[i - 2].text.startswith("BÀI") else i - 1
    starts[0] = 0  # a cover or preamble belongs to the first lesson
    parts = [lines[a:b] for a, b in zip(starts, [*starts[1:], len(lines)], strict=True)]
    merged: list[list[Line]] = []
    for p in parts:
        if merged and len(p) < 10:
            merged[-1].extend(p)
        else:
            merged.append(p)
    return merged


def _dates(text: str, year: int | None) -> list[date]:
    out: list[date] = []
    r = RANGE.search(text)
    if r:
        y = int(r.group(4)) if r.group(4) else year
        if y is not None:
            y = y + 2000 if y < 100 else y
            for d in (r.group(1), r.group(2)):
                try:
                    out.append(date(y, int(r.group(3)), int(d)))
                except ValueError:
                    pass
            return out
    for m in DATE.finditer(text):
        y = int(m.group(3)) if m.group(3) else year
        if y is None:
            continue
        y = y + 2000 if y < 100 else y
        try:
            out.append(date(y, int(m.group(2)), int(m.group(1))))
        except ValueError:
            pass
    return out


def metadata(lines: list[Line], doc: LessonDoc) -> None:
    head = lines[:30]
    text = [fold(ln.text) for ln in head]
    for raw, f in zip((ln.text for ln in head), text, strict=True):
        m = BAI.match(raw)
        if m and not doc.title:
            doc.title = (m.group(2) or "").strip()
            if not doc.title:
                nxt = next((ln.text for ln in head[head.index(next(x for x in head if x.text == raw)) + 1:] if not ln.header), "")
                doc.title = nxt[:120]
        if (t := re.search(r"tiet\s*(?:ppct)?\s*[:.]?\s*([\d][\d\s,\-–và]*)", f)) and not doc.ppct_period:
            doc.ppct_period = " ".join(t.group(1).split())[:30]
        if (w := re.search(r"tuan\s*[:.]?\s*(\d{1,2})", f)) and not doc.week:
            doc.week = w.group(1)
    joined = " | ".join(text)
    for subj, names in SUBJECTS.items():
        if doc.subject is None and any(re.search(rf"(?:ke hoach bai day|mon|bo mon)\s*[:\-]?\s*{n}", joined) or f" {n} 1" in f" {joined}"
                                       for n in names):
            doc.subject = subj
    if (g := re.search(r"(?:lop|dia li|dia ly|lich su|ngu van|vat li|hoa hoc|sinh hoc)\s*(10|11|12)\b", joined)):
        doc.grade = int(g.group(1))
    year: int | None = None
    for ln in head:
        f = fold(ln.text)
        if (s := re.search(r"ngay soan\s*[:.]?\s*(.+)", f)) and doc.planned_on is None:
            ds = [d for d in _dates(s.group(1), None) if 2020 <= d.year <= 2040]
            if ds:
                doc.planned_on, year = ds[0], ds[0].year
    for ln in lines[:40]:
        f = fold(ln.text)
        if (s := re.search(r"ngay day\s*[:.]?\s*(.+)", f)) and doc.taught_from is None:
            ds = [d for d in _dates(s.group(1), year) if 2020 <= d.year <= 2040]
            if ds:
                doc.taught_from, doc.taught_to = ds[0], ds[-1]


# ---------------------------------------------------------------- units
class _Unit:
    def __init__(self, kind: str, lines: list[Line]) -> None:
        self.kind, self.lines = kind, lines

    @property
    def text(self) -> str:
        return " ".join(ln.text for ln in self.lines)


def _mcq_end(lines: list[Line], i: int) -> int:
    """Index after the last line of the question starting at lines[i]."""
    j = i + 1
    seen = set(lines[i].opts) | {m.group(1) for m in OPTION.finditer(lines[i].text)}
    last = lines[i]
    while j < len(lines):
        ln = lines[j]
        f = fold(ln.text)
        if CAU.match(ln.text) or PART_II.match(f) or PART_III.match(f) or ACTIVITY.match(f) or ln.header or ln.table != last.table:
            break
        starts = {m.group(1) for m in OPTION.finditer(ln.text)}
        if starts or ln.opts:
            seen |= starts | set(ln.opts)
        elif len(seen) >= 4:  # all four options seen: only an indented or lower-case wrapped line continues the last option
            wrapped = ln.wrap_ok and (ln.x0 > last.x0 + 3 or ln.text[:1].islower()) and (ln.top - last.bottom) < 0.9 * max(1.0, last.bottom - last.top)
            if not wrapped:
                break
        last = ln
        j += 1
    return j


def _is_head(ln: Line) -> bool:
    f = fold(ln.text)
    return bool(PART_I.match(f) or PART_II.match(f) or PART_III.match(f) or ACTIVITY.match(f) or SUB.match(f) or OBJ_HEAD.match(f)
                or (len(ln.text) < 80 and ln.text.isupper())
                or (re.match(r"^\d+\s*[.)]\s", ln.text) and len(ln.text) < 50 and not ln.text.rstrip().endswith((".", ":", ";", "?", "!"))))


def _units(lines: list[Line]) -> list[_Unit]:
    out: list[_Unit] = []
    i = 0
    para: list[Line] = []

    def flush() -> None:
        nonlocal para
        if para:
            out.append(_Unit("text", para))
            para = []

    while i < len(lines):
        ln = lines[i]
        if CAU.match(ln.text):
            flush()
            j = _mcq_end(lines, i)
            out.append(_Unit("mcq", lines[i:j]))
            i = j
            continue
        if ln.table:
            flush()
            out.append(_Unit("cell", [ln]))
        elif ln.boxed:
            if para and not para[-1].boxed:
                flush()
            if out and out[-1].kind == "box" and out[-1].lines[-1].page == ln.page and not para:
                out[-1].lines.append(ln)
            elif para and para[-1].boxed:
                para.append(ln)
            else:
                flush()
                para = [ln]
            # boxed lines of one frame are one unit: close it when the next line leaves the frame
            if i + 1 >= len(lines) or not lines[i + 1].boxed or lines[i + 1].page != ln.page:
                out.append(_Unit("box", para))
                para = []
        elif _is_head(ln):
            flush()
            out.append(_Unit("text", [ln]))
        else:
            starts_new = bool(BULLET.match(ln.text)) or not para
            if para and not starts_new:
                prev = para[-1].text.rstrip()
                if prev.endswith((".", ":", ";", "!", "?")) and not ln.text[:1].islower():
                    starts_new = True
            if starts_new:
                flush()
            para.append(ln)
        i += 1
    flush()
    return out


def _parse_mcq(u: _Unit) -> tuple[str, list[tuple[str, str]], dict[str, bool]] | None:
    """(stem, [(letter, option text)], underlined letters) or None when it is an open question."""
    text = " ".join(ln.text for ln in u.lines)
    m = CAU.match(text)
    body = m.group(2) if m else text
    hits: list[tuple[str, int, int]] = []
    want = "A"
    for o in OPTION.finditer(body):
        if o.group(1) == want:
            hits.append((o.group(1), o.start(1), o.end()))
            want = chr(ord(want) + 1)
            if want > "D":
                break
    if len(hits) < 2:
        return None
    stem = body[: hits[0][1]].strip()
    opts = []
    for k, (letter, _, end) in enumerate(hits):
        stop = hits[k + 1][1] if k + 1 < len(hits) else len(body)
        opts.append((letter, body[end:stop].strip()))
    flags: dict[str, bool] = {}
    for ln in u.lines:
        for letter, v in ln.opts.items():
            flags[letter] = flags.get(letter, False) or v
    return stem, opts, flags


# ---------------------------------------------------------------- the state machine
@dataclass
class _State:
    part: str = ""
    obj_default: str | None = None
    section: Section | None = None
    activity_type: str | None = None
    para: int = 0


def parse_lesson(lines: list[Line], lesson_index: int, anchors: list[PAnchor]) -> LessonDoc:
    doc = LessonDoc()
    metadata(lines, doc)
    kept, doc.redacted = redact([ln for ln in lines if not ln.header])
    st = _State()
    cues = COMPETENCY_CUES.get(doc.subject or "", ())

    def add(kind: str, atype: AnchorType, ln: Line, text: str, extra: dict[str, int | str] | None = None) -> int:
        st.para += 1
        loc: dict[str, int | str] = {"page": ln.page, "para": st.para, "lesson": lesson_index, "type": atype}
        loc.update(extra or {})
        anchors.append(PAnchor(kind, atype, loc, text[:MAX_EXCERPT]))
        return len(anchors) - 1

    def section(kind: str, activity_type: str | None = None, sub: str | None = None) -> Section:
        s = Section(kind, activity_type, sub)
        doc.sections.append(s)
        st.section = s
        return s

    def attach(idx: int) -> None:
        if st.section is not None:
            st.section.anchors.append(idx)

    def competency(text: str) -> str | None:
        f = fold(text)
        return next((code for cue, code in cues if cue in f), st.obj_default)

    for u in _units(kept):
        f = fold(u.text)
        first = u.lines[0]
        if u.kind == "text":
            if PART_I.match(f):
                st.part, st.obj_default, st.activity_type = "muc_tieu", None, None
                section("objectives")
                continue
            if PART_II.match(f):
                st.part, st.activity_type = "thiet_bi", None
                section("equipment")
                continue
            if PART_III.match(f):
                st.part = "tien_trinh"
                section("process")
                continue
            am = ACTIVITY.match(f)
            if am:
                main, subn, name = int(am.group(1)), am.group(2), am.group(3)
                atype = next((t for cue, t in ACTIVITY_NAMES if cue in name), None) or BY_NUMBER.get(main)
                st.part = "tien_trinh"
                st.activity_type = atype
                section("sub" if subn else "activity", atype)
                attach(add("HEADING", "heading", first, u.text))
                continue
            if st.part == "tien_trinh" and (sm := SUB.match(f)) and len(f.split()) <= 8:
                section("sub", st.activity_type, SUB_KIND[sm.group(1)])
                attach(add("HEADING", "heading", first, u.text))
                continue
            if st.part == "tien_trinh" and STEP.match(f):
                section("step", st.activity_type, "to_chuc")
            if st.part == "muc_tieu" and (oh := OBJ_HEAD.match(f)):
                st.obj_default = KNOWLEDGE_DEFAULT.get(doc.subject or "") if oh.group(1) == "kien thuc" else None
                attach(add("HEADING", "heading", first, u.text))
                continue
            kind: str = "HEADING" if len(u.text) < 60 and u.text.isupper() else "PARAGRAPH"
            idx = add(kind, "heading" if kind == "HEADING" else "paragraph", first, u.text)
            attach(idx)
            if st.part == "muc_tieu" and kind == "PARAGRAPH":
                doc.objectives.append(Objective(u.text.lstrip("-•+* ").strip(), competency(u.text), idx))
            if FIGURE.match(f):
                anchors[idx].anchor_type = "figure_caption"
                anchors[idx].locator["type"] = "figure_caption"
        elif u.kind == "box":
            attach(add("PARAGRAPH", "knowledge_box", first, u.text))
        elif u.kind == "cell":
            attach(add("TABLE_CELL", "table_cell", first, u.text, {"row": st.para}))
        else:  # mcq
            parsed = _parse_mcq(u)
            if parsed is None:
                attach(add("PARAGRAPH", "paragraph", first, u.text))
                continue
            stem, opts, flags = parsed
            n = len(doc.mcqs) + 1
            stem_i = add("PARAGRAPH", "paragraph", first, stem, {"mcq": n, "part": "stem"})
            opt_i = [add("PARAGRAPH", "paragraph", first, text, {"mcq": n, "part": letter}) for letter, text in opts]
            for i in (stem_i, *opt_i):
                attach(i)
            under = [letter for letter, _ in opts if flags.get(letter)]
            one = len(under) == 1
            source = None if not one else ("underline" if first.wrap_ok else "docx_underline")
            doc.mcqs.append(Mcq(stem_i, opt_i, under[0] if one else None, source, not one))
    return doc


def parse_plan(lines: list[Line], pages: int) -> PlanFile:
    plan = PlanFile(pages=pages)
    for k, part in enumerate(split_lessons(lines)):
        doc = parse_lesson(part, k, plan.anchors)
        if plan.lessons:  # one file is one teacher's plans for one subject and grade: a later header may not repeat them
            doc.subject = doc.subject or plan.lessons[-1].subject
            doc.grade = doc.grade or plan.lessons[-1].grade
        plan.lessons.append(doc)
    return plan
