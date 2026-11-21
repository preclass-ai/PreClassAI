"""Synthetic CV 5512 lesson plans (PDF and DOCX) for tests. Invented content and fake names only: no real plan is copied here."""

import io
import os
from collections.abc import Callable

FONT_CANDIDATES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/Library/Fonts/Arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
)


def font_path() -> str | None:
    return next((p for p in FONT_CANDIDATES if os.path.exists(p)), None)


class PdfBuilder:
    def __init__(self, font: str, *, underline: str = "line", watermark: bool = True) -> None:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas

        pdfmetrics.registerFont(TTFont("F", font))
        self.buf = io.BytesIO()
        self.c = canvas.Canvas(self.buf, pagesize=A4)
        self.w, self.h = A4
        self.underline, self.watermark, self.page = underline, watermark, 0
        self.size, self.y, self.stringWidth = 11, 0.0, pdfmetrics.stringWidth
        self._new_page()

    def _new_page(self) -> None:
        if self.page:
            self.c.showPage()
        self.page += 1
        c = self.c
        if self.watermark:  # rotated, large, light grey
            c.saveState()
            c.setFillGray(0.85)
            c.setFont("F", 64)
            c.translate(120, 200)
            c.rotate(45)
            c.drawString(0, 0, "TÀI LIỆU ĐÃ BAN HÀNH")
            c.restoreState()
        c.setFillGray(0)
        c.setFont("F", 9)
        c.drawString(50, self.h - 30, "KẾ HOẠCH BÀI DẠY ĐỊA LÍ 10 - TRƯỜNG THPT MẪU - TỔ MẪU")  # repeated header
        c.drawString(self.w / 2 - 10, 25, f"Trang {self.page}")  # footer
        c.setFont("F", self.size)
        self.y = self.h - 70

    def line(self, text: str, x: float = 50, size: float | None = None, gap: float = 17) -> float:
        if self.y < 70:
            self._new_page()
        self.c.setFont("F", size or self.size)
        self.c.drawString(x, self.y, text)
        y = self.y
        self.y -= gap
        return y

    def mark(self, x0: float, x1: float, y: float) -> None:
        if self.underline == "line":
            self.c.line(x0, y - 2.2, x1, y - 2.2)
        else:
            self.c.rect(x0, y - 2.6, x1 - x0, 0.8, fill=1, stroke=0)

    def options(self, opts: list[str], underlined: str, *, one_line: bool, x: float = 60) -> None:
        """Options A..D; every letter in `underlined` gets an underline on the letter."""
        if one_line:
            s = "    ".join(f"{chr(65 + i)}. {o}" for i, o in enumerate(opts))
            y = self.line(s, x)
            for i in range(len(opts)):
                letter = chr(65 + i)
                if letter in underlined:
                    pre = "    ".join(f"{chr(65 + k)}. {opts[k]}" for k in range(i))
                    px = x + self.stringWidth(pre + ("    " if i else ""), "F", self.size)
                    self.mark(px, px + self.stringWidth(letter, "F", self.size), y)
        else:
            for i, o in enumerate(opts):
                letter = chr(65 + i)
                y = self.line(f"{letter}. {o}", x)
                if letter in underlined:
                    self.mark(x, x + self.stringWidth(letter, "F", self.size), y)

    def box(self, lines: list[str]) -> None:
        top = self.y + 12
        for t in lines:
            self.line(t, 62)
        self.c.rect(52, self.y + 8, self.w - 104, top - self.y - 8, stroke=1, fill=0)
        self.y -= 6

    def table(self, rows: list[list[str]]) -> None:
        top = self.y + 12
        for r in rows:
            y = self.y
            for j, cell in enumerate(r):
                self.c.drawString(60 + j * 150, y, cell)
            self.y -= 20
        bottom = self.y + 12
        for k in range(len(rows) + 1):
            self.c.line(55, top - k * 20, 55 + 150 * len(rows[0]), top - k * 20)
        for j in range(len(rows[0]) + 1):
            self.c.line(55 + j * 150, top, 55 + j * 150, bottom)
        self.y -= 6

    def page_break(self) -> None:
        self._new_page()

    def done(self) -> bytes:
        self.c.save()
        return self.buf.getvalue()


def plan_pdf(font: str, *, underline: str = "line", watermark: bool = True) -> bytes:
    p = PdfBuilder(font, underline=underline, watermark=watermark)
    p.line("BÀI 1: DÂN CƯ MẪU", size=14)
    p.line("Giáo viên: Lê Văn Giả")
    p.line("Tiết PPCT: 5    Tuần: 3")
    p.line("Ngày soạn: 01/09/2026")
    p.line("Ngày dạy: 08/09/2026")
    p.line("I. MỤC TIÊU")
    p.line("1. Kiến thức")
    p.line("- Trình bày được đặc điểm dân cư của nước Mẫu.")
    p.line("2. Năng lực")
    p.line("- Nhận thức khoa học địa lí: phân tích được số liệu dân số.")
    p.line("- Tìm hiểu địa lí: đọc được bảng số liệu.")
    p.line("3. Phẩm chất")
    p.line("- Chăm chỉ, trung thực.")
    p.line("II. THIẾT BỊ DẠY HỌC")
    p.line("- Bản đồ và bảng số liệu mẫu.")
    p.line("III. TIẾN TRÌNH DẠY HỌC")
    p.line("HOẠT ĐỘNG 1: MỞ ĐẦU")
    p.line("a) Mục tiêu: Tạo hứng thú cho học sinh.")
    p.line("b) Nội dung: Quan sát hình ảnh và trả lời câu hỏi.")
    p.line("c) Sản phẩm: Câu trả lời của học sinh.")
    p.line("d) Tổ chức thực hiện")
    p.line("Bước 1: GV chuyển giao nhiệm vụ cho cả lớp.")
    p.line("HOẠT ĐỘNG 2: HÌNH THÀNH KIẾN THỨC MỚI")
    p.line("Hoạt động 2.1: Tìm hiểu quy mô dân số")
    p.box(["Dân số nước Mẫu là 100 triệu người.", "Tỉ lệ gia tăng dân số là 1,2%."])
    p.table([["Vùng", "Dân số"], ["Vùng I", "30"], ["Vùng II", "45"]])
    p.line("Hình 1. Biểu đồ dân số mẫu")
    p.line("HOẠT ĐỘNG 3: LUYỆN TẬP")
    p.line("Câu 1. Vùng nào có dân số cao nhất?")
    p.options(["Vùng I", "Vùng II", "Vùng III", "Vùng IV"], "B", one_line=False)
    p.line("Câu 2. Chọn đáp án đúng về dân số.")
    p.options(["Một", "Hai", "Ba", "Bốn"], "C", one_line=True)
    p.line("Câu 3. Số liệu nào thuộc vùng I?")
    p.options(["30", "45", "60", "75"], "", one_line=False)
    p.line("Câu 4. Nhận định nào đúng?")
    p.options(["Nhận định một", "Nhận định hai", "Nhận định ba", "Nhận định bốn"], "AD", one_line=False)
    p.line("HOẠT ĐỘNG 4: VẬN DỤNG")
    p.line("Em hãy vẽ biểu đồ dân số của địa phương mình.")
    p.line("TỔ TRƯỞNG", x=80)
    p.line("Nguyễn Văn Mẫu", x=80)
    p.line("GIÁO VIÊN", x=300)
    p.line("Trần Thị Thử", x=300)

    p.page_break()
    p.line("BÀI 2: ĐÔ THỊ MẪU", size=14)
    p.line("Tiết PPCT: 6    Tuần: 4")
    p.line("Ngày soạn: 02/09/2026")
    p.line("Ngày dạy: 15/09/2026 - 16/09/2026")
    p.line("I. MỤC TIÊU")
    p.line("- Nhận thức khoa học địa lí: nêu được đặc điểm đô thị.")
    p.line("II. CHUẨN BỊ")
    p.line("- Bản đồ đô thị.")
    p.line("III. TIẾN TRÌNH")
    p.line("Hoạt động 1. Khởi động")
    p.line("Em có sống ở đô thị không?")
    p.line("Hoạt động 2. Khám phá")
    p.line("Đô thị hóa là quá trình tăng tỉ lệ dân thành thị.")
    p.line("Hoạt động 3. Luyện tập")
    p.line("Câu 1. Đô thị hóa là gì?")
    p.options(["Quá trình một", "Quá trình hai"], "", one_line=False)
    p.line("Câu 2. Đô thị lớn nhất nước Mẫu?")
    p.options(["Thành phố X", "Thành phố Y", "Thành phố Z", "Thành phố T"], "D", one_line=False)
    p.line("Hoạt động 4. Vận dụng")
    p.line("Tìm hiểu đô thị nơi em ở.")
    p.line("TỔ TRƯỞNG", x=80)
    p.line("Nguyễn Văn Mẫu", x=80)
    return p.done()


def plan_docx(build: Callable[[object], None] | None = None, *, subject: str = "ĐỊA LÍ", grade: int = 10) -> bytes:
    """A one-lesson plan with an underlined answer run. Another subject (for example LỊCH SỬ) must parse the same way."""
    from docx import Document

    d = Document()
    d.add_paragraph(f"KẾ HOẠCH BÀI DẠY MÔN {subject} {grade}")
    d.add_paragraph("BÀI 3: CHỦ ĐỀ MẪU")
    d.add_paragraph("Tiết PPCT: 7    Tuần: 5")
    d.add_paragraph("Ngày soạn: 03/09/2026")
    d.add_paragraph("Ngày dạy: 22/09/2026")
    for t in ("I. MỤC TIÊU", "- Nhận thức khoa học địa lí: nêu được khái niệm.", "II. THIẾT BỊ", "- Tranh ảnh.", "III. TIẾN TRÌNH",
              "HOẠT ĐỘNG 1: MỞ ĐẦU", "Em nghĩ gì về chủ đề này?", "HOẠT ĐỘNG 2: HÌNH THÀNH KIẾN THỨC MỚI", "Khái niệm mẫu là một ví dụ.",
              "HOẠT ĐỘNG 3: LUYỆN TẬP"):
        d.add_paragraph(t)
    for n, ans in ((1, "B"), (2, "")):
        d.add_paragraph(f"Câu {n}. Chọn đáp án đúng.")
        p = d.add_paragraph()
        for i, o in enumerate(("Một", "Hai", "Ba", "Bốn")):
            letter = chr(65 + i)
            r = p.add_run(letter)
            r.underline = letter == ans
            p.add_run(f". {o}    ")
    d.add_paragraph("HOẠT ĐỘNG 4: VẬN DỤNG")
    d.add_paragraph("Hãy áp dụng vào thực tế.")
    d.add_paragraph("GIÁO VIÊN")
    d.add_paragraph("Phạm Văn Thử")
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()
