"""Multi-format source files: DOCX, PDF, XLSX, PPTX -> anchors. Threats and tests: docs/security/THREAT-MODEL-upload.md.

The file type comes from magic bytes and `[Content_Types].xml`, never from the client's name or Content-Type. Zip-level
checks run in the API process (stdlib only);
everything that opens the file with a parsing library runs in a throw-away
child process with a timeout and a memory limit, so a hostile file can cost at most one killed child.
shortcut: no malware scan (D-001 #11), no OCR for scanned PDFs; RLIMIT_AS exists only on Linux (Render):
on Windows dev only the timeout applies.
"""

import asyncio
import io
import multiprocessing
import re
import time
import zipfile
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.errors import ApiError
from app.sources.parse import MAX_ANCHORS, OOXML, ParsedAnchor, _limit, check_ooxml, parse_docx

MIME = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "pdf": "application/pdf",
}
_ONLY = "Chỉ nhận tệp DOCX, PDF, XLSX hoặc PPTX"
_PDF_ACTIVE = (b"/JavaScript", b"/JS", b"/Launch", b"/EmbeddedFile", b"/OpenAction", b"/AA")
_MIN_TEXT_CHARS = 20  # fewer extractable characters than this in the whole PDF = scan
_SLOT = asyncio.Semaphore(1)  # one parse at a time: Render Free has 512 MB


@dataclass(frozen=True)
class Limits:
    pdf_pages: int = 50
    xlsx_sheets: int = 5
    xlsx_cells: int = 2000
    pptx_slides: int = 60
    timeout_s: int = 30
    mem_mb: int = 0


def detect_kind(data: bytes) -> str:
    """docx | xlsx | pptx | pdf, or ApiError. Zip safety (entries, size, ratio, macros, external parts) is checked here."""
    if data[:5] == b"%PDF-":
        return "pdf"
    if data[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":
        raise ApiError(422, "INVALID_FILE", "Office cũ (.doc/.xls/.ppt) không được nhận, hãy lưu thành .docx/.xlsx/.pptx")
    if data[:4] != b"PK\x03\x04":
        raise ApiError(422, "INVALID_FILE", _ONLY)
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            info = next((i for i in zf.infolist() if i.filename == "[Content_Types].xml"), None)
            if info is None or info.file_size > 1024 * 1024:
                raise ApiError(422, "INVALID_FILE", _ONLY)
            ctypes = zf.read(info).decode("utf-8", "replace")
    except zipfile.BadZipFile as e:
        raise ApiError(422, "INVALID_FILE", _ONLY) from e
    if "macroEnabled" in ctypes:
        raise ApiError(422, "MACRO_REJECTED", "Tệp chứa macro nên không được nhận")
    for kind, (_, marker, _) in OOXML.items():
        if marker in ctypes:
            check_ooxml(data, kind)  # bombs, entry count, macros, external content
            return kind
    raise ApiError(422, "INVALID_FILE", _ONLY)


# ---------------------------------------------------------------- parsers (run in the child process)
def _paragraphs(text: str) -> list[str]:
    blocks = [" ".join(b.split()) for b in re.split(r"\n\s*\n", text) if b.strip()]
    if len(blocks) == 1 and "\n" in text.strip():  # no blank lines: PDF text usually comes line by line
        blocks = [" ".join(ln.split()) for ln in text.splitlines() if ln.strip()]
    return blocks


def parse_pdf(data: bytes, lim: Limits) -> list[ParsedAnchor]:
    from pypdf import PdfReader

    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        if reader.is_encrypted:
            raise ApiError(422, "INVALID_FILE", "PDF có mật khẩu không được nhận")
        n = len(reader.pages)
        if n > lim.pdf_pages:
            raise ApiError(422, "SOURCE_TOO_LARGE", f"PDF có quá {lim.pdf_pages} trang")
        root: Any = reader.trailer["/Root"]
        names = root.get("/Names")
        names_keys = set(names.get_object().keys()) if names is not None else set()
        if {"/OpenAction", "/AA"} & set(root.keys()) or {"/JavaScript", "/EmbeddedFiles"} & names_keys:
            raise ApiError(422, "ACTIVE_CONTENT_REJECTED", "PDF chứa mã tự chạy hoặc tệp đính kèm nên không được nhận")
        out: list[ParsedAnchor] = []
        for i in range(n):
            page = reader.pages[i]
            for annot in page.get("/Annots") or []:
                action = annot.get_object().get("/A")
                if action is not None and action.get_object().get("/S") in ("/JavaScript", "/Launch"):
                    raise ApiError(422, "ACTIVE_CONTENT_REJECTED", "PDF chứa mã tự chạy nên không được nhận")
            for j, para in enumerate(_paragraphs(page.extract_text() or "")):
                kind = "HEADING" if i == 0 and j == 0 else "PARAGRAPH"
                out.append(ParsedAnchor(kind, {"page": i + 1, "para": j + 1}, para))
            if len(out) > MAX_ANCHORS:
                break
    except ApiError:
        raise
    except Exception as e:  # noqa: BLE001 pypdf raises many types on malformed files
        raise ApiError(422, "INVALID_FILE", "Không đọc được tệp PDF") from e
    if sum(len(a.excerpt) for a in out) < _MIN_TEXT_CHARS:
        raise ApiError(422, "SCANNED_PDF", "File là ảnh scan, vui lòng nạp bản có chữ (Word/PDF xuất từ Word)")
    return _limit(out)


def vn_number(v: Any) -> str:
    """A spreadsheet number as Vietnamese text ("23,2"): no thousands separator, so parse_numbers is unambiguous."""
    d = Decimal(repr(v)) if isinstance(v, float) else Decimal(v)
    return format(d.normalize(), "f").replace(".", ",")


def parse_xlsx(data: bytes, lim: Limits) -> list[ParsedAnchor]:
    from openpyxl import load_workbook  # type: ignore[import-untyped]

    out: list[ParsedAnchor] = []
    try:
        wb = load_workbook(io.BytesIO(data), read_only=True, data_only=True)  # stored values only: nothing is evaluated
        if len(wb.worksheets) > lim.xlsx_sheets:
            raise ApiError(422, "SOURCE_TOO_LARGE", f"Bảng tính có quá {lim.xlsx_sheets} sheet")
        for ws in wb.worksheets:
            headers: dict[int, str] = {}
            cells = 0
            for r, row in enumerate(ws.iter_rows(values_only=True)):
                if r > lim.xlsx_cells * 5:  # a sheet that claims a million empty rows
                    raise ApiError(422, "SOURCE_TOO_LARGE", "Sheet quá lớn")
                for c, v in enumerate(row):
                    if v is None or isinstance(v, bool) or (isinstance(v, str) and not v.strip()):
                        continue
                    cells += 1
                    if cells > lim.xlsx_cells:
                        raise ApiError(422, "SOURCE_TOO_LARGE", f"Sheet có quá {lim.xlsx_cells} ô")
                    numeric = isinstance(v, (int, float, Decimal))
                    text = vn_number(v) if numeric else " ".join(str(v).split())
                    loc: dict[str, Any] = {"sheet": ws.title, "row": r, "col": c}
                    if r == 0:
                        headers[c] = text
                    elif numeric and c in headers:
                        loc["header"] = headers[c]
                    out.append(ParsedAnchor("TABLE_CELL", loc, text))
    except ApiError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ApiError(422, "INVALID_FILE", "Không đọc được tệp XLSX") from e
    return _limit(out)


def parse_pptx(data: bytes, lim: Limits) -> list[ParsedAnchor]:
    from pptx import Presentation

    out: list[ParsedAnchor] = []
    try:
        prs = Presentation(io.BytesIO(data))
        if len(prs.slides) > lim.pptx_slides:
            raise ApiError(422, "SOURCE_TOO_LARGE", f"Bài trình chiếu có quá {lim.pptx_slides} slide")
        for s, slide in enumerate(prs.slides, start=1):
            title = slide.shapes.title
            for sh, shape in enumerate(slide.shapes):  # shortcut: shapes inside groups are skipped
                if shape.has_text_frame:
                    for p, para in enumerate(shape.text_frame.paragraphs):
                        text = " ".join(para.text.split())
                        if text:
                            kind = "HEADING" if title is not None and shape.shape_id == title.shape_id else "PARAGRAPH"
                            out.append(ParsedAnchor(kind, {"slide": s, "shape": sh, "para": p}, text))
                if shape.has_table:
                    for r, row in enumerate(shape.table.rows):
                        for c, cell in enumerate(row.cells):
                            text = " ".join(cell.text.split())
                            if text:
                                out.append(ParsedAnchor("TABLE_CELL", {"slide": s, "shape": sh, "row": r, "col": c}, text))
            if len(out) > MAX_ANCHORS:
                break
    except ApiError:
        raise
    except Exception as e:  # noqa: BLE001
        raise ApiError(422, "INVALID_FILE", "Không đọc được tệp PPTX") from e
    return _limit(out)


def parse_docx_file(data: bytes, lim: Limits) -> list[ParsedAnchor]:
    return parse_docx(data)


def _plan(data: bytes, lim: Limits) -> Any:
    from app.lessonplan import parse_plan_file

    return parse_plan_file(data, lim)


# "plan" returns a PlanFile (lesson plans, CV 5512), the others a list of anchors
PARSERS: dict[str, Any] = {"pdf": parse_pdf, "xlsx": parse_xlsx, "pptx": parse_pptx, "docx": parse_docx_file, "plan": _plan}


# ---------------------------------------------------------------- isolation
def _child(kind: str, data: bytes, lim: Limits, conn: Any, prog: Any = None) -> None:
    try:
        if kind == "plan" and prog is not None:
            from app.lessonplan.readers import set_progress

            set_progress(prog)
        if lim.mem_mb:
            try:
                import resource as res_mod

                res: Any = res_mod  # typeshed hides setrlimit on win32
                cap = lim.mem_mb * 1024 * 1024
                res.setrlimit(res.RLIMIT_AS, (cap, cap))
            except (ImportError, ValueError, OSError):  # Windows: no RLIMIT_AS
                pass
        conn.send(("ok", PARSERS[kind](data, lim)))
    except ApiError as e:
        conn.send(("api", e.status, e.code, e.title))
    except BaseException as e:  # noqa: BLE001 MemoryError etc.: report, never crash silently
        conn.send(("err", type(e).__name__))
    finally:
        conn.close()


Progress = Callable[[int, int], None]


def _run(kind: str, data: bytes, lim: Limits, progress: Progress | None = None) -> Any:
    ctx = multiprocessing.get_context("spawn")
    recv, send = ctx.Pipe(duplex=False)
    prog = ctx.Array("i", 2, lock=False)  # (page, pages) written by the child for kind "plan"
    proc = ctx.Process(target=_child, args=(kind, data, lim, send, prog), daemon=True)
    proc.start()
    send.close()
    try:
        deadline = time.monotonic() + lim.timeout_s
        while not recv.poll(0.5):
            if progress is not None:
                progress(prog[0], prog[1])
            if time.monotonic() > deadline:
                raise ApiError(422, "PARSE_TIMEOUT", f"Đọc tệp quá {lim.timeout_s} giây nên bị hủy")
        try:
            msg = recv.recv()
        except EOFError as e:  # the child died (killed by the memory limit, crash)
            raise ApiError(422, "INVALID_FILE", "Không đọc được tệp (hết bộ nhớ hoặc tệp lỗi)") from e
    finally:
        if proc.is_alive():
            proc.kill()
        proc.join(5)
        recv.close()
    if msg[0] == "ok":
        return msg[1]
    if msg[0] == "api":
        raise ApiError(msg[1], msg[2], msg[3])
    raise ApiError(422, "INVALID_FILE", "Không đọc được tệp")


async def parse_isolated(kind: str, data: bytes, lim: Limits, progress: Progress | None = None,
                         on_start: Callable[[], Any] | None = None) -> Any:
    async with _SLOT:
        if on_start is not None:
            await on_start()
        return await asyncio.to_thread(_run, kind, data, lim, progress)
