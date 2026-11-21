# PR D1: đọc giáo án CV 5512 (feat/lesson-plan-5512)

Base: main (a0bc6b0, đã có PR C). Migration 0007 chỉ thêm bảng. Không đổi API (chưa có endpoint, đó là PR D2).

## Làm gì
- `.gitignore` thêm `private/` (giáo án thật không bao giờ vào git).
- `app/lessonplan/`: đọc PDF từng trang (pdfplumber, không OCR; trang không có chữ báo cần DOCX) và DOCX; loại watermark (chữ xoay, hoặc to và xám nhạt), đánh dấu đầu/cuối trang lặp, che chữ ký và tên giáo viên, tách nhiều bài trong một tệp, metadata (môn, lớp, tên bài, Tiết PPCT, Tuần, Ngày soạn, Ngày dạy), cây 5512 (mục tiêu kèm mã năng lực, 4 hoạt động), khung kiến thức, bảng, chú thích hình, MCQ với đáp án từ gạch chân (đường hoặc hình chữ nhật mỏng; DOCX theo run.underline); 0 hoặc 2+ gạch thì `needs_confirmation`.
- Nhãn mô hình tùy chọn (`label.py`, mặc định tắt) chỉ gán nhãn hoạt động, id bịa bị loại, không viết lại nội dung, không bao giờ chọn đáp án.
- Chạy trong tiến trình con sẵn có (`PARSERS["plan"]`).
- Migration 0007: `subject_competency` (seed Địa lí), `lesson_plan`, `lesson_section`, `objective`, `extracted_mcq`.
- `scripts/ops/eval_lesson_plans.py`: thống kê cục bộ, không in nội dung.

## Kiểm tra
ruff, mypy --strict sạch; pytest 389 passed (21 test giáo án trên fixture bịa: gạch chân dạng đường và dạng hình chữ nhật, 0 và 2 gạch, watermark, đầu trang lặp, chữ ký bị che, nhiều bài một tệp, hai kiểu tiêu đề hoạt động, DOCX, môn khác (Lịch sử), tiến trình con, nhãn mô hình, schema).

## Số liệu trên 6 giáo án thật khác nhau (7 tệp, 1 trùng), chỉ thống kê
25 bài, 25/25 (100%) nhận đủ 4 hoạt động. 107 MCQ: 54 (50%) có đáp án từ gạch chân, 53 (50%) cần giáo viên xác nhận (một tệp 50 câu chỉ 9 câu có gạch; các câu còn lại không có dấu gạch nào trong PDF). Metadata: 5/25 bài chưa có Tiết PPCT hoặc tên, 24/25 chưa có Ngày dạy (hầu hết bài không in dòng này). 0 neo chứa tên giáo viên; 77 vùng đã che. Thời gian 21 đến 32 giây mỗi tệp 25 đến 42 trang, đỉnh bộ nhớ Python 30 đến 44MB.

## Rủi ro và việc phải biết
- Nên xin bản DOCX hoặc nhắc giáo viên gạch chân đáp án trước khi nạp: một nửa MCQ cần xác nhận tay.
- Hạn nộp tự tính từ Ngày dạy sẽ thường trống: D2 cần ô chọn tay.
- pdfminer chậm (0,5 giây mỗi trang): khi nạp qua API dùng timeout 120 giây cho loại "plan".
- Tên viết tự do giữa đoạn không bị bắt; chưa có OCR.
