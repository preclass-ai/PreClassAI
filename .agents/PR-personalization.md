# PR: Cá nhân hóa theo lựa chọn và hành vi của học sinh (feat/personalization)

Base: `feat/habit-chat` (phụ thuộc Habit; gộp Habit trước). ADR: `docs/adr/ADR-0013-personalization.md`.
**Nguyên tắc:** không thu, suy luận hay lưu nhãn tâm lý/sức khỏe nào (không MBTI, ADHD, trắc nghiệm tính cách). Chỉ có (1) lựa chọn do chính học sinh bật/tắt, mặc định tắt; (2) luật 0đ trên kết quả lần làm đầu và số lần dùng gợi ý, tính lại mỗi lần, không lưu.

## Làm gì
- Migration 0004 (chỉ thêm): `student_preference(student_id, key, value, updated_at)`, `key` bị CHECK vào 6 khóa cố định.
- API: `GET|PUT|DELETE /v1/student/preferences`; `/habit` thêm `advice` (REVIEW/QUIET) + `preview` (Gợi ý 1 mở sẵn, không tính là đã dùng gợi ý); `/auth/config.personalizationEnabled`; CSV khảo sát thêm cờ `pref_*` và `focus_mode_used`. Cờ `PERSONALIZATION_ENABLED` (mặc định tắt): tắt thì 404 và UI ẩn.
- Habit đọc lựa chọn: `chia_nho_tung_buoc` rút gợi ý còn một câu ngắn; `uu_tien_bang_so_lieu` làm bậc 2 nhắc bảng số liệu trước. Chỉ đổi cách diễn đạt.
- UI S07: "Em muốn học theo cách nào hôm nay?" (4 lựa chọn + hẹn giờ 5/10 phút + Tắt hết), Chế độ tập trung (1 câu/màn hình, thanh tiến độ, hẹn giờ + nhắc nghỉ, nội dung bài thu gọn), thanh nhắc tiến độ, banner "xem lại nội dung" cho kỹ năng REVIEW, nút nhạt hơn cho kỹ năng QUIET.

## Kiểm tra
- pytest (trước khi thêm UI): 281 passed + 1 test Habit cập nhật cho field mới, sau đó chạy lại `test_habit.py` 17/17 và `test_personalization.py` 9/9; ruff, mypy --strict sạch; OpenAPI + api-client sinh lại. Lần chạy toàn bộ cuối cùng chưa lặp lại sau commit frontend (backend không đổi).
- Test chặn nhãn tâm lý: `test_no_psychological_labels_in_code` quét `apps/api/app`, `alembic`, `apps/web/src|app` tìm mbti/adhd/personality/autis/dyslex/tính cách/rối loạn/learning_style: 0 kết quả; `student_preference` chỉ có 4 cột (test).
- Red team (`scripts/ops/habit_redteam.py`) với **cả 4 tổ hợp** lựa chọn: 12 câu × 59 tấn công × 4 tổ hợp + gợi ý, rule + llm-mock: **0 vi phạm**; thêm unit test tham số hóa `small × table_first`.
- Web: lint, typecheck sạch; vitest 50 passed (có test PersonalizationBar, FocusTimer).
- **Chưa chạy:** Playwright `tests/e2e/personalization.spec.ts` (390/768/1280/WebKit) và ảnh before/after. Lần chạy bị hệ thống dừng vì thiếu RAM trên máy dev; spec đã viết sẵn. Chạy lại: bật API với `CHAT_ENABLED=true PERSONALIZATION_ENABLED=true`, dev DB đã seed, rồi `E2E_WEBKIT=1 npx playwright test tests/e2e/personalization.spec.ts` (dùng HS10-01..04, chạy 1 lần mỗi lần seed).

## Env đề xuất trên Render
`CHAT_ENABLED=true`, `PERSONALIZATION_ENABLED=true`. Chạy `alembic upgrade head` (0004) trước.

## Rủi ro
Chưa có kiểm tra giao diện thật ở 4 viewport. Lời khuyên REVIEW/QUIET chỉ hiện cho chính em (giáo viên không thấy); nếu muốn báo cáo cho giáo viên cần ADR riêng. Seed chỉ có 1 bài published nên chưa có dữ liệu thật để kiểm chứng ngưỡng 2 câu/50% (test dùng ngưỡng hạ thấp).
