"""In-memory fixtures for the multi-format upload tests: valid files with fictional Geography data (DỮ LIỆU MINH HỌA)
and hostile ones (docs/security/THREAT-MODEL-upload.md). Nothing here comes from a real lesson plan."""

import io
import zipfile

NOTE = "DU LIEU MINH HOA"
ROWS = [("Dong bang song Hong", 23.2), ("Tay Nguyen", 5.9), ("Dong Nam Bo", 17.8)]
_CT = {
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
}


def ooxml(kind: str, extra: dict[str, bytes] | None = None, macro: bool = False, entries: int = 0) -> bytes:
    """A minimal zip that passes the content-type sniffing (not a loadable document): base for hostile variants."""
    ct = _CT[kind].replace("sheet.main", "sheet.macroEnabled.main") if macro else _CT[kind]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", f'<Types><Override PartName="/x" ContentType="{ct}"/></Types>')
        for name, data in (extra or {}).items():
            z.writestr(name, data)
        for i in range(entries):
            z.writestr(f"junk/{i}.txt", b"x")
    return buf.getvalue()


def bomb(kind: str) -> bytes:
    return ooxml(kind, {"data/big.bin": b"\0" * (30 * 1024 * 1024)})  # ~30 KB on disk, 30 MB unzipped


# ---------------------------------------------------------------- valid
def xlsx() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.title = "Dan so"
    ws.append(["Vung", "So dan (trieu nguoi)"])
    for name, v in ROWS:
        ws.append([name, v])
    ws["A6"] = NOTE
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def xlsx_formula() -> bytes:
    from openpyxl import Workbook

    wb = Workbook()
    ws = wb.active
    ws.append(["Vung", "So dan"])
    ws.append(["Tay Nguyen", "=SUM(1,2)"])  # saved without a cached value: must not be evaluated or kept
    ws.append(["Dong Nam Bo", "=cmd|' /C calc'!A0"])
    ws.append(["Ha Noi", 8.5])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def pptx() -> bytes:
    from pptx import Presentation
    from pptx.util import Inches

    prs = Presentation()
    s1 = prs.slides.add_slide(prs.slide_layouts[1])
    s1.shapes.title.text = "Phan bo dan cu"
    s1.placeholders[1].text = f"Dan cu phan bo khong deu. {NOTE}"
    s2 = prs.slides.add_slide(prs.slide_layouts[5])
    s2.shapes.title.text = "Bang so lieu"
    tbl = s2.shapes.add_table(2, 2, Inches(1), Inches(2), Inches(4), Inches(1)).table
    for r, row in enumerate([["Vung", "So dan"], ["Tay Nguyen", "5,9"]]):
        for c, v in enumerate(row):
            tbl.cell(r, c).text = v
    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def docx() -> bytes:
    from docx import Document

    d = Document()
    d.add_heading("Phan bo dan cu", 1)
    d.add_paragraph(f"Dan cu phan bo khong deu. {NOTE}")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def _pdf(pages: list[str], catalog_extra: str = "") -> bytes:
    """Tiny hand-built PDF (Helvetica, ASCII text): one content stream per page."""
    objs: list[bytes] = []
    n = len(pages)
    kids = " ".join(f"{3 + 2 * i} 0 R" for i in range(n))
    objs.append(f"<< /Type /Catalog /Pages 2 0 R {catalog_extra}>>".encode())
    objs.append(f"<< /Type /Pages /Kids [{kids}] /Count {n} >>".encode())
    for i, text in enumerate(pages):
        content = text.encode()
        objs.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Contents {4 + 2 * i} 0 R "
                    "/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> >> >> >>".encode())
        objs.append(b"<< /Length %d >>\nstream\n" % len(content) + content + b"\nendstream")
    out = bytearray(b"%PDF-1.4\n")
    offs = []
    for i, o in enumerate(objs, start=1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    for o in offs:
        out += f"{o:010d} 00000 n \n".encode()
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    return bytes(out)


def _text(*lines: str) -> str:
    return "BT /F1 12 Tf 72 780 Td 20 TL " + " T* ".join(f"({ln}) Tj" for ln in lines) + " ET"


def pdf() -> bytes:
    return _pdf([_text("Phan bo dan cu", f"Dan cu phan bo khong deu {NOTE}"), _text("Trang hai: Tay Nguyen 5,9 trieu nguoi")])


def pdf_scan() -> bytes:
    return _pdf(["0.9 g 50 50 400 400 re f"])  # a filled rectangle and no text: what an image-only page looks like to a parser


def pdf_js() -> bytes:
    return _pdf([_text("Xin chao")], "/OpenAction << /S /JavaScript /JS (app.alert\\(1\\)) >> ")


def pdf_embedded() -> bytes:
    return _pdf([_text("Xin chao")], "/Names << /EmbeddedFiles << /Names [] >> >> ")


def pdf_encrypted() -> bytes:
    from pypdf import PdfReader, PdfWriter

    w = PdfWriter(clone_from=PdfReader(io.BytesIO(pdf())))
    w.encrypt("secret")
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def pdf_many_pages(n: int = 51) -> bytes:
    return _pdf([_text(f"Trang {i} co chu du dai de khong bi coi la scan") for i in range(n)])


PNG = b"\x89PNG\r\n\x1a\n" + b"\0" * 64
EXE = b"MZ\x90\x00" + b"\0" * 64
OLE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\0" * 64
