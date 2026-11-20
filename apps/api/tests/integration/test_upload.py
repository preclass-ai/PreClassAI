"""POST /v1/sources/file against a real database: every format, hostile files, ownership (THREAT-MODEL-upload.md)."""

from typing import Any

import httpx
import pytest

from app.sources.parse import MAX_UPLOAD_BYTES
from tests import upload_fixtures as fx
from tests.conftest import login

pytestmark = pytest.mark.db
TEACHER, OTHER, STUDENT = "gv.dia@preclass.local", "gv.khac@preclass.local", "HS10-01"


async def upload(c: httpx.AsyncClient, data: bytes, name: str = "giao-an.bin", ctype: str = "application/octet-stream",
                 **form: str) -> httpx.Response:
    return await c.post("/v1/sources/file", files={"file": (name, data, ctype)}, data={"title": "Nguồn thử", **form})


async def anchors(c: httpx.AsyncClient, src: dict[str, Any]) -> list[dict[str, Any]]:
    r = await c.get(f"/v1/source-revisions/{src['latestRevision']['id']}/anchors")
    assert r.status_code == 200
    return list(r.json()["items"])


@pytest.mark.parametrize("make,mime,name", [
    (fx.xlsx, "spreadsheetml.sheet", "so-lieu.xlsx"), (fx.pptx, "presentationml.presentation", "bai.pptx"),
    (fx.pdf, "application/pdf", "bai.pdf"), (fx.docx, "wordprocessingml.document", "bai.docx")])
async def test_valid_formats_create_a_source_with_anchors(client: httpx.AsyncClient, make: Any, mime: str, name: str) -> None:
    await login(client, TEACHER)
    r = await upload(client, make(), name)
    assert r.status_code == 201, r.text
    rev = r.json()["latestRevision"]
    assert mime in rev["mime"] and rev["extractStatus"] == "OK" and rev["extractError"] is None and rev["anchorCount"] >= 2
    assert all(a["locator"] for a in await anchors(client, r.json()))


async def test_xlsx_anchor_has_sheet_row_col_header_and_numbers(client: httpx.AsyncClient) -> None:
    await login(client, TEACHER)
    got = await anchors(client, (await upload(client, fx.xlsx(), "a.xlsx")).json())
    cell = next(a for a in got if a["excerpt"] == "23,2")
    assert cell["kind"] == "TABLE_CELL" and cell["numbers"] == [23.2]
    assert cell["locator"] == {"sheet": "Dan so", "row": 1, "col": 1, "header": "So dan (trieu nguoi)"}


async def test_type_comes_from_magic_bytes_not_the_name(client: httpx.AsyncClient) -> None:
    await login(client, TEACHER)
    r = await upload(client, fx.docx(), "that-ra-la-docx.pdf", "application/pdf")
    assert r.status_code == 201 and "wordprocessingml" in r.json()["latestRevision"]["mime"]
    for blob, name in ((fx.PNG, "a.pdf"), (fx.EXE, "a.docx"), (fx.OLE, "a.xlsx"), (b"hello", "a.pptx")):
        bad = await upload(client, blob, name, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        assert bad.status_code == 422 and bad.json()["code"] == "INVALID_FILE", name


async def test_scanned_pdf_is_stored_as_failed_with_a_clear_code(client: httpx.AsyncClient) -> None:
    await login(client, TEACHER)
    r = await upload(client, fx.pdf_scan(), "scan.pdf")
    assert r.status_code == 201
    rev = r.json()["latestRevision"]
    assert (rev["extractStatus"], rev["extractError"], rev["anchorCount"]) == ("FAILED", "SCANNED_PDF", 0)


@pytest.mark.parametrize("name,make,code", [
    ("bomb.xlsx", lambda: fx.bomb("xlsx"), "FILE_TOO_LARGE"), ("bomb.pptx", lambda: fx.bomb("pptx"), "FILE_TOO_LARGE"),
    ("bomb.docx", lambda: fx.bomb("docx"), "FILE_TOO_LARGE"),
    ("entries.xlsx", lambda: fx.ooxml("xlsx", entries=1001), "INVALID_FILE"),
    ("macro.xlsx", lambda: fx.ooxml("xlsx", macro=True), "MACRO_REJECTED"),
    ("macro.pptx", lambda: fx.ooxml("pptx", {"ppt/vbaProject.bin": b"x"}), "MACRO_REJECTED"),
    ("external.xlsx", lambda: fx.ooxml("xlsx", {"xl/externalLinks/externalLink1.xml": b"<x/>"}), "EXTERNAL_CONTENT_REJECTED"),
    ("embedded.pptx", lambda: fx.ooxml("pptx", {"ppt/embeddings/o.bin": b"x"}), "EXTERNAL_CONTENT_REJECTED"),
    ("js.pdf", fx.pdf_js, "ACTIVE_CONTENT_REJECTED"), ("attach.pdf", fx.pdf_embedded, "ACTIVE_CONTENT_REJECTED"),
    ("locked.pdf", fx.pdf_encrypted, "INVALID_FILE"), ("pages.pdf", fx.pdf_many_pages, "SOURCE_TOO_LARGE"),
    ("traversal.xlsx", lambda: fx.ooxml("xlsx", {"../evil": b"x"}), "INVALID_FILE"),
    ("big.pdf", lambda: b"%PDF-" + b"0" * MAX_UPLOAD_BYTES, "FILE_TOO_LARGE")])
async def test_hostile_files_are_rejected_and_nothing_is_stored(client: httpx.AsyncClient, name: str, make: Any, code: str) -> None:
    await login(client, TEACHER)
    before = len((await client.get("/v1/sources")).json()["items"])
    r = await upload(client, make(), name)
    assert r.status_code == 422 and r.json()["code"] == code, r.text
    assert len((await client.get("/v1/sources")).json()["items"]) == before


async def test_formula_values_are_not_evaluated(client: httpx.AsyncClient) -> None:
    await login(client, TEACHER)
    got = await anchors(client, (await upload(client, fx.xlsx_formula(), "f.xlsx")).json())
    assert not any("=" in a["excerpt"] or "cmd" in a["excerpt"] for a in got)
    assert "8,5" in [a["excerpt"] for a in got]


async def test_ownership_and_roles(client: httpx.AsyncClient) -> None:
    await login(client, TEACHER)
    src = (await upload(client, fx.xlsx(), "a.xlsx")).json()
    rev = src["latestRevision"]["id"]
    await client.post("/v1/auth/logout")
    await login(client, OTHER)
    assert (await client.get(f"/v1/sources/{src['id']}")).status_code == 404  # PRIVATE source of another teacher
    assert (await client.get(f"/v1/source-revisions/{rev}/anchors")).status_code == 404
    assert all(i["id"] != src["id"] for i in (await client.get("/v1/sources")).json()["items"])
    await client.post("/v1/auth/logout")
    await login(client, STUDENT)
    assert (await upload(client, fx.xlsx(), "a.xlsx")).status_code == 403


async def test_school_visibility_still_needs_a_licence_note(client: httpx.AsyncClient) -> None:
    await login(client, TEACHER)
    r = await upload(client, fx.xlsx(), "a.xlsx", visibility="SCHOOL")
    assert r.status_code == 422 and r.json()["code"] == "LICENSE_REQUIRED"
    assert (await upload(client, fx.xlsx(), "a.xlsx", visibility="SCHOOL", licenseNote="Minh họa")).status_code == 201


async def test_a_failed_source_cannot_feed_a_lesson(client: httpx.AsyncClient) -> None:
    await login(client, TEACHER)
    scan = (await upload(client, fx.pdf_scan(), "scan.pdf")).json()
    r = await client.post("/v1/lessons", json={"title": "Bài thử", "grade": 10, "sourceRevisionIds": [scan["latestRevision"]["id"]]})
    assert r.status_code == 422 and r.json()["code"] == "SOURCE_NOT_READABLE"
    ok = (await upload(client, fx.xlsx(), "a.xlsx")).json()
    r = await client.post("/v1/lessons", json={"title": "Bài thử", "grade": 10, "sourceRevisionIds": [ok["latestRevision"]["id"]]})
    assert r.status_code == 201
