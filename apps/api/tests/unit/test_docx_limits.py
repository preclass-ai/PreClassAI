"""DOCX is untrusted input: zip bombs, macros, embedded and external content are refused before python-docx opens it."""
import io
import zipfile

import pytest
from docx import Document

from app.errors import ApiError
from app.sources.parse import MAX_ENTRIES, check_docx_container, parse_docx


def good_docx() -> bytes:
    d = Document()
    d.add_paragraph("Số dân (triệu người): 23,2")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def with_parts(parts: dict[str, bytes], deflate: int = zipfile.ZIP_DEFLATED) -> bytes:
    """The good document plus extra parts."""
    src = zipfile.ZipFile(io.BytesIO(good_docx()))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", deflate) as z:
        for i in src.infolist():
            z.writestr(i, src.read(i))
        for name, data in parts.items():
            z.writestr(name, data)
    return out.getvalue()


def code(data: bytes) -> str:
    with pytest.raises(ApiError) as e:
        check_docx_container(data)
    return e.value.code


def test_a_normal_document_passes() -> None:
    check_docx_container(good_docx())
    assert parse_docx(good_docx())


def test_zip_bomb_by_ratio_is_refused() -> None:
    bomb = with_parts({"word/bomb.xml": b"0" * (15 * 1024 * 1024)})  # ~15 MB of zeros -> ~15 KB
    assert len(bomb) < 100_000 and code(bomb) == "FILE_TOO_LARGE"


def test_total_uncompressed_size_is_capped_at_20mb() -> None:
    import os

    big = with_parts({"word/big.bin.xml": os.urandom(21 * 1024 * 1024)}, zipfile.ZIP_STORED)  # incompressible: ratio ~1
    assert len(big) > 10 * 1024 * 1024 and code(big) == "FILE_TOO_LARGE"  # 10 MB upload limit trips first or the 20 MB cap


def test_too_many_entries_are_refused() -> None:
    many = with_parts({f"word/p{i}.xml": b"<a/>" for i in range(MAX_ENTRIES + 1)})
    assert code(many) == "INVALID_FILE"


@pytest.mark.parametrize("name", ["word/vbaProject.bin", "x/macro.docm"])
def test_macros_are_refused(name: str) -> None:
    assert code(with_parts({name: b"x"})) == "MACRO_REJECTED"


def test_macro_enabled_content_type_is_refused() -> None:
    src = zipfile.ZipFile(io.BytesIO(good_docx()))
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as z:
        for i in src.infolist():
            data = src.read(i)
            if i.filename == "[Content_Types].xml":
                data = data.replace(b"document.main+xml", b"document.macroEnabled.main+xml")
            z.writestr(i, data)
    assert code(out.getvalue()) == "MACRO_REJECTED"


@pytest.mark.parametrize("name", ["word/embeddings/oleObject1.bin", "word/activeX/activeX1.xml"])
def test_embedded_objects_are_refused(name: str) -> None:
    assert code(with_parts({name: b"x"})) == "EXTERNAL_CONTENT_REJECTED"


def rels(rel: str) -> bytes:
    return ('<?xml version="1.0"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f"{rel}</Relationships>").encode()


def test_external_template_or_linked_file_is_refused() -> None:
    bad = rels('<Relationship Id="r9" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/attachedTemplate"'
               ' Target="file:///C:/x.dotm" TargetMode="External"/>')
    assert code(with_parts({"word/_rels/settings.xml.rels": bad})) == "EXTERNAL_CONTENT_REJECTED"


def test_plain_external_hyperlink_is_allowed() -> None:
    ok = rels('<Relationship Id="r8" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"'
              ' Target="https://example.com" TargetMode="External"/>')
    check_docx_container(with_parts({"word/_rels/extra.xml.rels": ok}))
