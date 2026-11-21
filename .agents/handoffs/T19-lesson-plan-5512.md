# T19 Giáo án 5512, PR D1

| Skill | Bước | Kết quả |
|---|---|---|
| security-threat-model | trước khi code | thêm L-01..L-04 vào `THREAT-MODEL-habit.md` (tên giáo viên, PDF độc, đáp án do mô hình đoán, rò giáo án thật) |
| security-best-practices | sau khi code | parser chạy trong tiến trình con có timeout, không nhận PDF mã tự chạy, không log nội dung, script chỉ in số liệu |
| playwright-cli, web-design-guidelines, design-taste-frontend | không dùng ở D1 | D1 chưa có giao diện (thuộc D2) |
| humanizer | tài liệu | PR và ADR viết ngắn, không gạch dài |

Giáo án thật ở `private/giao-an/` (đã thêm vào `.gitignore`), chỉ đọc cục bộ. Không có nội dung nào trong repo, test, docs hay log.
Lệnh đo: `cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/eval_lesson_plans.py`.

## Cập nhật 21/11/2026 (yêu cầu P0/P1 sau khi D1 đến D4 được push)
- Skill dùng: ponytail (lite) cho cách làm gọn; humanizer cho câu chữ giao diện và tài liệu mới (không dùng dấu gạch ngang dài, xưng "em", "HABIT AI"); không dùng skill nào khác.
- **Hiệu năng đọc giáo án** (Docker python:3.12-slim, `--memory=512m`, giáo án thật, chỉ số): 0,5 CPU: 25 đến 42 trang mất 11 đến 22 s; 0,1 CPU (mức Render Free): 31 trang 80 s, 40 trang 102 s; RSS đỉnh 97 đến 127 MB. Hồ sơ cProfile: khoảng 90% thời gian ở pdfminer (diễn giải luồng nội dung, ~0,3 s mỗi trang, mỗi trang khoảng 2.200 đối tượng chữ), không phải ở mã của mình. Chưa đổi sang PyMuPDF vì giấy phép AGPL; pypdfium2 sẽ phải viết lại cách dò gạch chân, rủi ro cao sát hạn. Giữ timeout 120 s (đặt qua `PLAN_PARSE_TIMEOUT_S`); ở 0,1 CPU file 40 trang chỉ còn dư 18 s, nên khuyến nghị Render gói 0,5 CPU trở lên hoặc nâng timeout lên 240 s (job nền, không chặn yêu cầu).
- Job nền, mã năng lực, `teachDate`, heatmap, dạy lại idempotent: xem PR D2, D3 và `docs/api/API_GUIDE.md` mục 16 và 17.
