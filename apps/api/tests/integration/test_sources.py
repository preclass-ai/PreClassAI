"""GĐ5: sources (text/DOCX -> anchors), revisions with new hashes, and IDOR/role checks (§10.1)."""

import io
import re
import uuid
import zipfile
from pathlib import Path

import httpx
import pytest
from docx import Document

from app.config import get_settings
from app.ids import uid
from tests.conftest import login

pytestmark = pytest.mark.db

PRIVATE_OF_DIA = uid("dien-tich-rung:asset")  # PRIVATE, owner gv.dia
SCHOOL_OF_DIA = uid("dan-so-vung:asset")  # SCHOOL, owner gv.dia
PRIVATE_OF_KHAC = uid("xuat-khau:asset")  # PRIVATE, owner gv.khac
DOCX_CT = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def make_docx(extra: str = "") -> bytes:
    d = Document()
    d.add_heading("Dân số các vùng (DỮ LIỆU MINH HỌA)", level=1)
    d.add_paragraph("Năm 2020, số dân đồng bằng sông Hồng đạt 23,2 triệu người." + extra)
    t = d.add_table(rows=2, cols=2)
    t.cell(0, 0).text, t.cell(0, 1).text = "Vùng", "Số dân (triệu người)"
    t.cell(1, 0).text, t.cell(1, 1).text = "Tây Nguyên", "5.9"
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def zip_with(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items():
            z.writestr(n, b)
    return buf.getvalue()


async def upload(c: httpx.AsyncClient, data: bytes, name: str = "bai.docx", path: str = "/v1/sources/docx",
                 **form: str) -> httpx.Response:
    return await c.post(path, files={"file": (name, data, DOCX_CT)}, data={"title": "Tài liệu thử", **form})


async def anchors(c: httpx.AsyncClient, source: dict) -> list[dict]:  # type: ignore[type-arg]
    r = await c.get(f"/v1/source-revisions/{source['latestRevision']['id']}/anchors")
    assert r.status_code == 200
    return r.json()["items"]  # type: ignore[no-any-return]


# ----------------------------------------------------------------------------- parsing
async def test_text_source_creates_anchors_with_numbers(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await client.post("/v1/sources", json={"title": "Bài đọc", "text": "Tiêu đề\n\nDiện tích 3.120,5 nghìn ha.\n\nHết."})
    assert r.status_code == 201, r.text
    src = r.json()
    assert src["latestRevision"]["version"] == 1 and src["latestRevision"]["anchorCount"] == 3
    items = await anchors(client, src)
    assert [a["kind"] for a in items] == ["HEADING", "PARAGRAPH", "PARAGRAPH"]
    assert items[1]["numbers"] == [3120.5] and items[1]["locator"] == {"para_index": 1}
    assert re.fullmatch(r"anc_[0-9a-f]{8}_001", items[0]["code"])


async def test_docx_paragraphs_headings_and_table_cells(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await upload(client, make_docx())
    assert r.status_code == 201, r.text
    src = r.json()
    assert src["latestRevision"]["mime"] == DOCX_CT and src["latestRevision"]["extractStatus"] == "OK"
    items = await anchors(client, src)
    kinds = [(a["kind"], a["locator"]) for a in items]
    assert kinds[0][0] == "HEADING" and kinds[1][0] == "PARAGRAPH"
    cells = [a for a in items if a["kind"] == "TABLE_CELL"]
    assert [c["locator"] for c in cells] == [
        {"table": 0, "row": 0, "col": 0}, {"table": 0, "row": 0, "col": 1},
        {"table": 0, "row": 1, "col": 0}, {"table": 0, "row": 1, "col": 1}]
    assert cells[3]["excerpt"] == "5.9" and cells[3]["numbers"] == [5.9]
    assert "Dân số" in items[0]["excerpt"] and "DỮ LIỆU MINH HỌA" in items[0]["excerpt"]  # diacritics kept


async def test_uploaded_file_is_stored_under_random_name_not_client_name(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    r = await upload(client, make_docx(), name="../../evil.docx")
    assert r.status_code == 201
    stored = sorted(p.name for p in Path(get_settings().upload_dir).iterdir())
    assert stored and all(re.fullmatch(r"[0-9a-f-]{36}\.(docx|pdf|xlsx|pptx)", n) for n in stored)
    assert not (Path(get_settings().upload_dir).parent / "evil.docx").exists()


# ----------------------------------------------------------------------------- rejected uploads
@pytest.mark.parametrize(
    ("data", "code"),
    [
        (b"not a docx at all", "INVALID_FILE"),
        (b"PK\x03\x04garbage", "INVALID_FILE"),
        (zip_with({"readme.txt": b"hi"}), "INVALID_FILE"),  # a zip without [Content_Types].xml
        (zip_with({"[Content_Types].xml": b"<Types>macroEnabled wordprocessingml.document.main+xml</Types>",
                   "word/vbaProject.bin": b"x"}), "MACRO_REJECTED"),
        (zip_with({"[Content_Types].xml": b"<Types/>", "../evil.xml": b"x"}), "INVALID_FILE"),
        (zip_with({"[Content_Types].xml": b"<Types>wordprocessingml.document.main+xml</Types>",
                   "bomb.bin": b"0" * (60 * 1024 * 1024)}), "FILE_TOO_LARGE"),  # >50 MB once unpacked
        (b"PK" + b"0" * (10 * 1024 * 1024 + 1), "FILE_TOO_LARGE"),
    ],
    ids=["not-zip", "bad-zip", "no-content-types", "macro", "path-traversal", "zip-bomb", "over-10MB"],
)
async def test_bad_uploads_are_422_and_store_nothing(client: httpx.AsyncClient, data: bytes, code: str) -> None:
    await login(client, "gv.dia@preclass.local")
    before = len(list(Path(get_settings().upload_dir).glob("*"))) if Path(get_settings().upload_dir).exists() else 0
    r = await upload(client, data)
    assert r.status_code == 422 and r.json()["code"] == code, r.text
    after = len(list(Path(get_settings().upload_dir).glob("*"))) if Path(get_settings().upload_dir).exists() else 0
    assert after == before


async def test_school_visibility_requires_license_note(client: httpx.AsyncClient) -> None:  # VAL-09
    await login(client, "gv.dia@preclass.local")
    r = await client.post("/v1/sources", json={"title": "x", "text": "a\n\nb", "visibility": "SCHOOL"})
    assert r.status_code == 422 and r.json()["code"] == "LICENSE_REQUIRED"
    ok = await client.post("/v1/sources", json={"title": "x", "text": "a\n\nb", "visibility": "SCHOOL",
                                                 "licenseNote": "DỮ LIỆU MINH HỌA"})
    assert ok.status_code == 201


# ----------------------------------------------------------------------------- AT-08 (part 1): new revision, new hash
async def test_new_revision_has_new_hash_and_does_not_touch_lessons(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    v1 = (await upload(client, make_docx())).json()
    edited = make_docx(" Đã sửa.")  # one byte string: zip entries carry the current second, so two builds can differ
    r = await upload(client, edited, path=f"/v1/sources/{v1['id']}/revisions/docx")
    assert r.status_code == 201, r.text
    v2 = r.json()["latestRevision"]
    assert v2["version"] == 2 and v2["sha256"] != v1["latestRevision"]["sha256"] and v2["id"] != v1["latestRevision"]["id"]
    same = await upload(client, edited, path=f"/v1/sources/{v1['id']}/revisions/docx")
    assert same.status_code == 409 and same.json()["code"] == "SOURCE_UNCHANGED"
    t = await client.post(f"/v1/sources/{v1['id']}/revisions", json={"text": "Mới\n\nHoàn toàn khác."})
    assert t.status_code == 201 and t.json()["latestRevision"]["version"] == 3


# ----------------------------------------------------------------------------- §10.1 IDOR / roles
async def test_other_teachers_private_source_is_404_everywhere(client: httpx.AsyncClient) -> None:
    await login(client, "gv.khac@preclass.local")
    sid = PRIVATE_OF_DIA
    rev = uid("dien-tich-rung:srcrev")
    assert (await client.get(f"/v1/sources/{sid}")).status_code == 404
    assert (await client.get(f"/v1/source-revisions/{rev}/anchors")).status_code == 404
    assert (await client.post(f"/v1/sources/{sid}/revisions", json={"text": "a\n\nb"})).status_code == 404
    assert (await upload(client, make_docx(), path=f"/v1/sources/{sid}/revisions/docx")).status_code == 404
    listed = {s["id"] for s in (await client.get("/v1/sources")).json()["items"]}
    assert str(sid) not in listed and str(PRIVATE_OF_KHAC) in listed and str(SCHOOL_OF_DIA) in listed


async def test_school_source_is_readable_but_not_writable_by_other_teachers(client: httpx.AsyncClient) -> None:
    await login(client, "gv.khac@preclass.local")
    assert (await client.get(f"/v1/sources/{SCHOOL_OF_DIA}")).status_code == 200
    rev = uid("dan-so-vung:srcrev")
    assert (await client.get(f"/v1/source-revisions/{rev}/anchors")).status_code == 200
    assert (await client.post(f"/v1/sources/{SCHOOL_OF_DIA}/revisions", json={"text": "a\n\nb"})).status_code == 404


async def test_random_ids_are_404_not_500(client: httpx.AsyncClient) -> None:
    await login(client, "gv.dia@preclass.local")
    for path in (f"/v1/sources/{uuid.uuid4()}", f"/v1/source-revisions/{uuid.uuid4()}/anchors"):
        assert (await client.get(path)).status_code == 404


@pytest.mark.parametrize("who", ["HS10-01", "admin@preclass.local"])
async def test_students_and_admin_cannot_use_sources(client: httpx.AsyncClient, who: str) -> None:
    await login(client, who)
    calls = [
        client.get("/v1/sources"), client.get(f"/v1/sources/{SCHOOL_OF_DIA}"),
        client.get(f"/v1/source-revisions/{uid('dan-so-vung:srcrev')}/anchors"),
        client.post("/v1/sources", json={"title": "x", "text": "a\n\nb"}),
        upload(client, make_docx()),
    ]
    for coro in calls:
        r = await coro
        assert r.status_code == 403 and r.json()["code"] == "FORBIDDEN_ROLE"


async def test_reviewer_can_read_but_not_create(client: httpx.AsyncClient) -> None:
    await login(client, "reviewer@preclass.local")
    assert (await client.get(f"/v1/sources/{SCHOOL_OF_DIA}")).status_code == 200
    assert (await client.get(f"/v1/sources/{PRIVATE_OF_DIA}")).status_code == 404
    assert (await client.post("/v1/sources", json={"title": "x", "text": "a\n\nb"})).status_code == 403


async def test_unauthenticated_is_401(client: httpx.AsyncClient) -> None:
    assert (await client.get("/v1/sources")).status_code == 401
    assert (await client.post("/v1/sources", json={"title": "x", "text": "a"})).status_code == 401


async def test_owner_id_in_body_is_ignored(client: httpx.AsyncClient) -> None:
    await login(client, "gv.khac@preclass.local")
    r = await client.post("/v1/sources", json={"title": "x", "text": "a\n\nb", "ownerId": str(uid("user:gv.dia"))})
    assert r.status_code == 201 and r.json()["ownerId"] == str(uid("user:gv.khac"))
