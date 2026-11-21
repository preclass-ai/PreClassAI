# PR D3: bảng insight v2 và đề xuất dạy lại (feat/insights-v2)

Xếp chồng trên D2 (feat/preclass-from-plan) và D1. Migration 0009 (cột `remediation_draft`, chỉ thêm). Biến mới: `DEMO_REPLAY` (mặc định false).

## Làm gì
- Insight theo câu: phương án sai hay chọn, bậc gợi ý cao nhất, cờ "Cần dạy lại", 2 chủ đề câu hỏi mỗi câu kèm ví dụ ẩn danh; số lần HABIT AI từ chối theo lý do. Chỉ giáo viên của lớp, không tên, không xếp hạng.
- "Đề xuất dạy lại": bản nháp gồm đoạn nguồn trích nguyên văn (VAL-01..10, chưa duyệt) cộng 3 câu luyện thêm qua Generate (mock khi LLM tắt).
- `DEMO_REPLAY=true`: phân tích trả bản ghi sẵn, nhãn "replay".

## Kiểm tra
Test tích hợp mới (3) và vitest mới (1); Playwright insights và plans 390, 768, 1280, WebKit xanh. Ảnh: `.agents/screens-insights2/`.

## Chưa làm
Replay từ một lần chạy model thật (P2, sau thi); câu luyện thêm sinh qua Generate chưa mang nhãn dạy lại.

## Bổ sung 21/11
Heatmap câu x năng lực; "Đề xuất dạy lại" idempotent; nhãn "Bản nháp dạy lại" ở hàng duyệt.
