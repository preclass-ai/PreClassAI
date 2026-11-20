"""Source parsing: pasted text and DOCX -> anchors (paragraphs, headings, table cells).

DOCX is untrusted input: magic bytes, content types, size/entry-count/compression-ratio limits, macro, embedded and
external-content rejection happen
BEFORE python-docx opens it. shortcut: no malware scan (D-001 #11); add one before accepting files from outside
the school.
"""

import io
import re
import zipfile
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from app.errors import ApiError
from app.hashing import excerpt_hash
from app.sources.numbers import parse_numbers

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 20 * 1024 * 1024  # checked on the zip directory, before extraction
MAX_ENTRIES = 1000
MAX_RATIO = 100  # uncompressed / compressed; real documents are ~3-15, a zip bomb is 1000+
RATIO_FREE_BYTES = 1024 * 1024  # small parts may compress extremely well (repeated XML): only judge parts above this
MAX_RELS_BYTES = 1024 * 1024
_REL = re.compile(r"<Relationship\b[^>]*>", re.I)
_EXTERNAL = re.compile(r'TargetMode\s*=\s*"External"', re.I)
_HYPERLINK = re.compile(r'Type\s*=\s*"[^"]*/hyperlink"', re.I)
MAX_ANCHORS = 5000
DOCX_MAIN = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


@dataclass
class ParsedAnchor:
    kind: str  # HEADING | PARAGRAPH | TABLE_CELL
    locator: dict[str, Any]
    excerpt: str

    @property
    def hash(self) -> str:
        return excerpt_hash(self.excerpt)

    @property
    def numbers(self) -> list[Decimal]:
        return parse_numbers(self.excerpt)


def _limit(anchors: list[ParsedAnchor]) -> list[ParsedAnchor]:
    if not anchors:
        raise ApiError(422, "EMPTY_SOURCE", "Tài liệu không có nội dung văn bản")
    if len(anchors) > MAX_ANCHORS:
        raise ApiError(422, "SOURCE_TOO_LARGE", "Tài liệu quá dài")
    return anchors


def _table_rows(block: str) -> list[list[str]] | None:
    """A block of >= 2 lines where every line has `|` or a tab is a table (markdown separator lines are skipped)."""
    lines = [ln.strip() for ln in block.split("\n") if ln.strip()]
    if len(lines) < 2 or not all("|" in ln or "\t" in ln for ln in lines):
        return None
    rows = [[" ".join(c.split()) for c in ln.strip("|").replace("\t", "|").split("|")] for ln in lines
            if set(ln) - set("|-: \t")]
    return rows if len(rows) >= 2 and all(len(r) >= 2 for r in rows) else None


def parse_text(text: str) -> list[ParsedAnchor]:
    """Blank-line separated blocks; the first is the heading. A `|`/tab-separated block is a table (TABLE_CELL anchors)."""
    out: list[ParsedAnchor] = []
    table_i = 0
    for i, block in enumerate(b for b in text.replace("\r\n", "\n").split("\n\n") if b.strip()):
        rows = _table_rows(block) if i else None
        if rows is None:
            out.append(ParsedAnchor("HEADING" if i == 0 else "PARAGRAPH", {"para_index": i}, " ".join(block.split())))
            continue
        out += [ParsedAnchor("TABLE_CELL", {"table": table_i, "row": r, "col": c}, cell)
                for r, row in enumerate(rows) for c, cell in enumerate(row) if cell]
        table_i += 1
    return _limit(out)


def check_docx_container(data: bytes) -> None:
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", "Tệp vượt quá 10 MB")
    if data[:2] != b"PK":
        raise ApiError(422, "INVALID_FILE", "Chỉ nhận tệp DOCX")
    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        infos = zf.infolist()
        if len(infos) > MAX_ENTRIES:
            raise ApiError(422, "INVALID_FILE", "Tệp DOCX có quá nhiều thành phần")
        total = sum(i.file_size for i in infos)
        if total > MAX_UNCOMPRESSED_BYTES:
            raise ApiError(422, "FILE_TOO_LARGE", "Tệp giải nén quá lớn")
        if any(i.file_size > RATIO_FREE_BYTES and i.file_size > MAX_RATIO * max(i.compress_size, 1) for i in infos) or (
                total > RATIO_FREE_BYTES and total > MAX_RATIO * len(data)):
            raise ApiError(422, "FILE_TOO_LARGE", "Tệp nén bất thường (nghi zip bomb)")
        names = [i.filename for i in infos]
        if any(".." in n.split("/") or n.startswith("/") for n in names):
            raise ApiError(422, "INVALID_FILE", "Tệp DOCX không hợp lệ")
        if any("vbaproject" in n.lower() or n.lower().endswith((".docm", ".dotm")) for n in names):
            raise ApiError(422, "MACRO_REJECTED", "Tệp chứa macro nên không được nhận")
        if any(n.lower().startswith(("word/embeddings/", "word/activex/")) for n in names):
            raise ApiError(422, "EXTERNAL_CONTENT_REJECTED", "Tệp chứa đối tượng nhúng nên không được nhận")
        for i in infos:  # linked templates/images/OLE/frames point outside the file: only plain hyperlinks are allowed
            if i.filename.lower().endswith(".rels"):
                if i.file_size > MAX_RELS_BYTES:
                    raise ApiError(422, "INVALID_FILE", "Tệp DOCX không hợp lệ")
                for rel in _REL.findall(zf.read(i).decode("utf-8", "replace")):
                    if _EXTERNAL.search(rel) and not _HYPERLINK.search(rel):
                        raise ApiError(422, "EXTERNAL_CONTENT_REJECTED", "Tệp liên kết tới nội dung ngoài nên không được nhận")
        if "[Content_Types].xml" not in names:
            raise ApiError(422, "INVALID_FILE", "Chỉ nhận tệp DOCX")
        ctypes = zf.read("[Content_Types].xml").decode("utf-8", "replace")
    except zipfile.BadZipFile as e:
        raise ApiError(422, "INVALID_FILE", "Chỉ nhận tệp DOCX") from e
    if "macroEnabled" in ctypes:
        raise ApiError(422, "MACRO_REJECTED", "Tệp chứa macro nên không được nhận")
    if "wordprocessingml.document.main+xml" not in ctypes:
        raise ApiError(422, "INVALID_FILE", "Chỉ nhận tệp DOCX")


def parse_docx(data: bytes) -> list[ParsedAnchor]:
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    check_docx_container(data)
    try:
        doc = Document(io.BytesIO(data))
    except Exception as e:  # noqa: BLE001 python-docx raises many types on malformed XML
        raise ApiError(422, "INVALID_FILE", "Không đọc được tệp DOCX") from e
    out: list[ParsedAnchor] = []
    para_i = table_i = 0
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            p = Paragraph(child, doc)
            text = " ".join(p.text.split())
            if text:
                style = (p.style.name if p.style is not None and p.style.name else "") or ""
                kind = "HEADING" if style.startswith(("Heading", "Title")) else "PARAGRAPH"
                out.append(ParsedAnchor(kind, {"para_index": para_i}, text))
            para_i += 1
        elif tag == "tbl":
            for r, row in enumerate(Table(child, doc).rows):
                seen: set[int] = set()
                for c, cell in enumerate(row.cells):
                    if id(cell._tc) in seen:  # noqa: SLF001 merged cells repeat the same element
                        continue
                    seen.add(id(cell._tc))  # noqa: SLF001
                    text = " ".join(cell.text.split())
                    if text:
                        out.append(ParsedAnchor("TABLE_CELL", {"table": table_i, "row": r, "col": c}, text))
            table_i += 1
        if len(out) > MAX_ANCHORS:
            break
    return _limit(out)
