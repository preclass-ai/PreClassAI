# ruff: noqa: E501  (regex tables and Vietnamese cue lists read better on one line)
"""Page-by-page readers: PDF (pdfplumber, no OCR) and DOCX. They return `Line`s; all meaning is decided in structure.py.

PDF: watermark characters (rotated, or oversized light grey) are dropped before lines are built; repeated first/last
lines of a page are flagged `header`; a framed rectangle marks a knowledge box; a thin horizontal line or rect just under
an option letter marks the underlined (correct) option. Memory: one page at a time, the page cache is flushed after each.
"""

import io
import re
import statistics
from collections import Counter
from typing import Any

from app.errors import ApiError
from app.lessonplan.model import Line

OPTION = re.compile(r"(?:(?<=\s)|^)([A-D])\s*[.)]")
_LETTER_AFTER = {".", ")"}
THIN = 1.5  # points: an underline is a line or a rect at most this tall
UNDER_GAP = 3.0  # points between the letter's bottom and the underline
MIN_TEXT = 20


def _rotated(c: dict[str, Any]) -> bool:
    m = c.get("matrix") or (1, 0, 0, 1, 0, 0)
    return (not c.get("upright", True)) or abs(m[1]) > 0.1 or abs(m[2]) > 0.1


def _light_grey(c: dict[str, Any]) -> bool:
    col = c.get("non_stroking_color")
    if not isinstance(col, (tuple, list)) or not col:
        return False
    vals = [float(v) for v in col]
    return all(0.55 <= v < 1.0 for v in vals) and max(vals) - min(vals) < 0.08


def is_watermark(c: dict[str, Any], median_size: float) -> bool:
    return _rotated(c) or (c["size"] > 2.5 * median_size and _light_grey(c))


def _thin_lines(page: Any) -> list[tuple[float, float, float]]:
    """(x0, x1, y) of every thin horizontal line or rect, as underline candidates."""
    out = [(float(r["x0"]), float(r["x1"]), (float(r["top"]) + float(r["bottom"])) / 2) for r in page.rects if r["height"] <= THIN]
    out += [(float(x["x0"]), float(x["x1"]), (float(x["top"]) + float(x["bottom"])) / 2) for x in page.lines if abs(x["top"] - x["bottom"]) <= THIN]
    return [t for t in out if t[1] - t[0] > 2 and t[1] - t[0] < 0.6 * float(page.width)]


def underlined(ch: dict[str, Any], lines: list[tuple[float, float, float]]) -> bool:
    w = float(ch["x1"]) - float(ch["x0"])
    for x0, x1, y in lines:
        overlap = min(float(ch["x1"]), x1) - max(float(ch["x0"]), x0)
        if overlap >= 0.5 * w and float(ch["bottom"]) - 3.5 <= y <= float(ch["bottom"]) + UNDER_GAP:
            return True
    return False


def option_flags(chars: list[dict[str, Any]], lines: list[tuple[float, float, float]]) -> dict[str, bool]:
    """Option letters of one line (`A.`, `B)`...) -> is the letter underlined."""
    flags: dict[str, bool] = {}
    for i, c in enumerate(chars):
        t = c["text"]
        if t in "ABCD" and i + 1 < len(chars) and chars[i + 1]["text"] in _LETTER_AFTER and (
                i == 0 or chars[i - 1]["text"].isspace() or float(c["x0"]) - float(chars[i - 1]["x1"]) > 0.25 * float(c["size"])):
            flags[t] = flags.get(t, False) or underlined(c, lines)
    return flags


def _frames(page: Any) -> list[tuple[float, float, float, float]]:
    return [(float(r["x0"]), float(r["top"]), float(r["x1"]), float(r["bottom"])) for r in page.rects
            if r["height"] > 15 and r["width"] > 0.35 * float(page.width) and r["width"] < 0.995 * float(page.width)]


def _inside(box: tuple[float, float, float, float], x0: float, top: float, x1: float, bottom: float) -> bool:
    return box[0] - 2 <= x0 and x1 <= box[2] + 2 and box[1] - 2 <= top and bottom <= box[3] + 2


def _tables(page: Any) -> tuple[list[tuple[float, float, float, float]], list[tuple[float, float, float, float]]]:
    """(rows of real tables, single-cell frames): a framed single cell is a knowledge box even when a table touches it."""
    rows: list[tuple[float, float, float, float]] = []
    frames: list[tuple[float, float, float, float]] = []
    try:
        for t in page.find_tables():
            for r in t.rows:
                box = tuple(float(v) for v in r.bbox)
                (rows if sum(1 for c in r.cells if c is not None) >= 2 else frames).append(box)  # type: ignore[arg-type]
    except Exception:  # noqa: BLE001, S110 pdfminer raises many types on odd layouts: no tables on this page
        return [], []
    return rows, frames


def _norm_hf(t: str) -> str:
    return re.sub(r"\d+", "#", " ".join(t.split()).lower())


def read_pdf(data: bytes, max_pages: int = 50) -> tuple[list[Line], int]:
    import pdfplumber

    lines: list[Line] = []
    try:
        pdf = pdfplumber.open(io.BytesIO(data))
    except Exception as e:  # noqa: BLE001
        raise ApiError(422, "INVALID_FILE", "Không đọc được tệp PDF") from e
    with pdf:
        n = len(pdf.pages)
        if n > max_pages:
            raise ApiError(422, "SOURCE_TOO_LARGE", f"PDF có quá {max_pages} trang")
        for pi in range(n):
            page = pdf.pages[pi]
            try:
                chars = page.chars
                if chars:
                    med = statistics.median(c["size"] for c in chars)
                    def keep_obj(o: dict[str, Any], med: float = med) -> bool:
                        return o.get("object_type") != "char" or not is_watermark(o, med)

                    keep = page.filter(keep_obj)
                    rows = keep.extract_text_lines(return_chars=True, strip=True)
                    thin = _thin_lines(page)
                    tables, cells = _tables(page)
                    frames = _frames(page) + cells
                    for r in rows:
                        text = " ".join(str(r["text"]).split())
                        if not text:
                            continue
                        x0, top, x1, bottom = float(r["x0"]), float(r["top"]), float(r["x1"]), float(r["bottom"])
                        in_table = any(_inside(t, x0, top, x1, bottom) for t in tables)
                        lines.append(Line(
                            text, pi + 1, x0, top, bottom,
                            boxed=(not in_table) and any(_inside(f, x0, top, x1, bottom) for f in frames),
                            table=in_table, opts=option_flags(r["chars"], thin)))
            finally:
                page.flush_cache()  # one page in memory at a time
                getattr(page, "close", lambda: None)()
    if sum(len(ln.text) for ln in lines) < MIN_TEXT:
        raise ApiError(422, "SCANNED_PDF", "Trang không có lớp chữ. Vui lòng nạp bản có chữ (DOCX hoặc PDF xuất từ Word)")
    _flag_headers(lines, n)
    return lines, n


def _flag_headers(lines: list[Line], pages: int) -> None:
    """First and last two lines of a page that repeat on at least half the pages (and 3+) are header/footer."""
    by_page: dict[int, list[Line]] = {}
    for ln in lines:
        by_page.setdefault(ln.page, []).append(ln)
    cand: dict[int, list[Line]] = {p: ls[:2] + ls[-2:] for p, ls in by_page.items()}
    seen = Counter(_norm_hf(ln.text) for ls in cand.values() for ln in {id(x): x for x in ls}.values())
    limit = max(3, pages // 2)
    for ls in cand.values():
        for ln in ls:
            if seen[_norm_hf(ln.text)] >= limit or re.fullmatch(r"(trang\s*)?\d{1,3}(\s*/\s*\d{1,3})?", ln.text.strip().lower()):
                ln.header = True


# ---------------------------------------------------------------- DOCX
def read_docx(data: bytes) -> tuple[list[Line], int]:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    from app.sources.parse import check_docx_container

    check_docx_container(data)
    try:
        doc = Document(io.BytesIO(data))
    except Exception as e:  # noqa: BLE001
        raise ApiError(422, "INVALID_FILE", "Không đọc được tệp DOCX") from e
    out: list[Line] = []

    def add(p: Any, table: bool) -> None:
        text = " ".join(p.text.split())
        if not text:
            return
        # an option letter is underlined when the run that holds it is underlined
        runs = list(p.runs)
        full = "".join(r.text for r in runs)
        ends = [sum(len(r.text) for r in runs[: i + 1]) for i in range(len(runs))]
        flags: dict[str, bool] = {}
        for m in OPTION.finditer(full):
            run = next((r for r, e in zip(runs, ends, strict=True) if m.start(1) < e), None)
            flags[m.group(1)] = flags.get(m.group(1), False) or bool(run is not None and run.underline)
        out.append(Line(text, 1, table=table, wrap_ok=False, opts=flags))

    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            add(Paragraph(child, doc), False)
        elif tag == "tbl":
            for row in Table(child, doc).rows:
                seen: set[int] = set()
                for cell in row.cells:
                    if id(cell._tc) in seen:  # noqa: SLF001 merged cells repeat the same element
                        continue
                    seen.add(id(cell._tc))  # noqa: SLF001
                    for p in cell.paragraphs:
                        add(p, True)
    return out, 1
