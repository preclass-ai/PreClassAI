"""Multi-format parsers and the hostile-file gate, without a database (THREAT-MODEL-upload.md U-01..U-10, U-12)."""

import pytest

from app.errors import ApiError
from app.sources import formats
from app.sources.formats import Limits, detect_kind, parse_pdf, parse_pptx, parse_xlsx, vn_number
from tests import upload_fixtures as fx

LIM = Limits()


def code(fn, *a) -> str:  # type: ignore[no-untyped-def]
    with pytest.raises(ApiError) as e:
        fn(*a)
    return e.value.code


def test_xlsx_locators_numbers_and_header_label() -> None:
    out = parse_xlsx(fx.xlsx(), LIM)
    cell = next(a for a in out if a.excerpt == "23,2")
    assert cell.kind == "TABLE_CELL" and cell.locator == {"sheet": "Dan so", "row": 1, "col": 1, "header": "So dan (trieu nguoi)"}
    assert [float(n) for n in cell.numbers] == [23.2]
    assert next(a for a in out if a.excerpt == "Tay Nguyen").locator == {"sheet": "Dan so", "row": 2, "col": 0}


def test_vn_number_is_unambiguous() -> None:
    assert [vn_number(x) for x in (23.2, 4015.8, 1000, 7, 0.05)] == ["23,2", "4015,8", "1000", "7", "0,05"]


def test_xlsx_formulas_are_never_evaluated_or_kept() -> None:
    out = parse_xlsx(fx.xlsx_formula(), LIM)
    texts = [a.excerpt for a in out]
    assert "8,5" in texts and not any("=" in t or "cmd" in t or t == "3" for t in texts)


def test_pptx_locators() -> None:
    out = parse_pptx(fx.pptx(), LIM)
    title = next(a for a in out if a.excerpt == "Phan bo dan cu")
    assert title.kind == "HEADING" and title.locator["slide"] == 1 and "para" in title.locator
    cell = next(a for a in out if a.excerpt == "5,9")
    assert cell.kind == "TABLE_CELL" and cell.locator["slide"] == 2 and (cell.locator["row"], cell.locator["col"]) == (1, 1)
    assert [float(n) for n in cell.numbers] == [5.9]


def test_pdf_pages_and_paragraphs() -> None:
    out = parse_pdf(fx.pdf(), LIM)
    assert out[0].kind == "HEADING" and out[0].locator == {"page": 1, "para": 1}
    assert any(a.locator["page"] == 2 and "Tay Nguyen 5,9" in a.excerpt for a in out)
    assert any(float(n) == 5.9 for a in out for n in a.numbers)


def test_scanned_pdf_and_active_pdf() -> None:
    assert code(parse_pdf, fx.pdf_scan(), LIM) == "SCANNED_PDF"
    assert code(parse_pdf, fx.pdf_js(), LIM) == "ACTIVE_CONTENT_REJECTED"
    assert code(parse_pdf, fx.pdf_embedded(), LIM) == "ACTIVE_CONTENT_REJECTED"
    assert code(parse_pdf, fx.pdf_encrypted(), LIM) == "INVALID_FILE"
    assert code(parse_pdf, fx.pdf_many_pages(), Limits(pdf_pages=50)) == "SOURCE_TOO_LARGE"
    assert code(parse_pdf, b"%PDF-1.4 garbage", LIM) == "INVALID_FILE"


def test_xlsx_and_pptx_limits() -> None:
    assert code(parse_xlsx, fx.xlsx(), Limits(xlsx_cells=3)) == "SOURCE_TOO_LARGE"
    assert code(parse_xlsx, fx.xlsx(), Limits(xlsx_sheets=0)) == "SOURCE_TOO_LARGE"
    assert code(parse_pptx, fx.pptx(), Limits(pptx_slides=1)) == "SOURCE_TOO_LARGE"


@pytest.mark.parametrize("data,kind", [(fx.xlsx(), "xlsx"), (fx.pptx(), "pptx"), (fx.docx(), "docx"), (fx.pdf(), "pdf")])
def test_detect_kind_by_magic_bytes(data: bytes, kind: str) -> None:
    assert detect_kind(data) == kind


@pytest.mark.parametrize("kind", ["docx", "xlsx", "pptx"])
def test_zip_bomb_and_many_entries_rejected(kind: str) -> None:
    assert code(detect_kind, fx.bomb(kind)) == "FILE_TOO_LARGE"
    assert code(detect_kind, fx.ooxml(kind, entries=1001)) == "INVALID_FILE"


def test_macros_external_and_traversal_rejected() -> None:
    assert code(detect_kind, fx.ooxml("xlsx", macro=True)) == "MACRO_REJECTED"
    assert code(detect_kind, fx.ooxml("pptx", {"ppt/vbaProject.bin": b"x"})) == "MACRO_REJECTED"
    assert code(detect_kind, fx.ooxml("docx", {"word/vbaProject.bin": b"x"})) == "MACRO_REJECTED"
    assert code(detect_kind, fx.ooxml("xlsx", {"xl/externalLinks/externalLink1.xml": b"<x/>"})) == "EXTERNAL_CONTENT_REJECTED"
    assert code(detect_kind, fx.ooxml("pptx", {"ppt/embeddings/oleObject1.bin": b"x"})) == "EXTERNAL_CONTENT_REJECTED"
    assert code(detect_kind, fx.ooxml("xlsx", {"../evil.txt": b"x"})) == "INVALID_FILE"


def test_fake_extension_and_legacy_formats_rejected() -> None:
    for blob in (fx.PNG, fx.EXE, fx.OLE, b"", b"PK\x03\x04 not really a zip"):
        assert code(detect_kind, blob) == "INVALID_FILE"


def test_parser_child_is_killed_on_timeout() -> None:
    assert code(formats._run, "xlsx", fx.xlsx(), Limits(timeout_s=0)) == "PARSE_TIMEOUT"  # noqa: SLF001
    assert [a.excerpt for a in formats._run("xlsx", fx.xlsx(), Limits(timeout_s=60))][:2] == ["Vung", "So dan (trieu nguoi)"]  # noqa: SLF001
