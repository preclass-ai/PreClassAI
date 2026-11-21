# PR C: góc nhìn giáo viên (feat/teacher-insights)

Base: `main` (bd975ca). Migration: không có mới. Chỉ thêm field/endpoint API (trừ mã lỗi nộp quá hạn, xem dưới).

## Làm gì
1. **"Học sinh hỏi gì"** trong "Lớp & bài giao" (mở "Xem tiến độ và câu hỏi"): câu hỏi HABIT AI nhóm bằng luật 0đ (bắt đầu, tìm số liệu, cách tính, đơn vị, khái niệm, so sánh, xin đáp án, khác), 3 ví dụ mỗi nhóm, bảng từng câu (đúng ngay lần đầu, gợi ý đã dùng, số câu hỏi). Ẩn danh: không có tên, mã hay số điện thoại. Nút **"AI phân tích"** (khi `CHAT_MODE=llm`; nếu không là "Tóm tắt chủ đề vướng" bằng luật) cho 3 đến 5 chủ đề, một lời gọi, cache 10 phút, tính ngân sách token.
2. **"AI gợi ý bài tập thêm"**: từ kỹ năng có tỉ lệ đúng lần đầu thấp nhất tạo **bản nháp** 3 câu bằng pipeline Generate sẵn có (bản mới + `append`). Khối AI_PROPOSED, qua VAL-01..10, giáo viên duyệt như mọi khối; không tự giao. Mock khi LLM tắt. Chỉ tác giả bài thấy nút.
3. **Hạn nộp**: ô "Ngày học" khi giao bài đặt hạn vào 23:59 ngày trước đó (sửa được). Học sinh thấy hạn dd/mm/yyyy ở mọi lớp (bỏ ẩn cho lớp khảo sát và khách). Quá hạn: vẫn xem được bài và lời giải, nộp trả 409 **`PAST_DUE`** (đổi từ `ASSIGNMENT_CLOSED`; giao diện chấp nhận cả hai) kèm câu thân thiện.
4. **Quyền**: chỉ TEACHER là thành viên lớp của assignment; người khác 404 (không 403), học sinh 403. Test IDOR: giáo viên không thuộc lớp, sai lớp, sai assignment.

## Kiểm tra
ruff, mypy --strict sạch; pytest 362 passed, 1 skipped (thêm 6 test tích hợp và 1 unit); OpenAPI (52 operation) và `schema.d.ts` sinh lại. Web lint, typecheck sạch; vitest 67. Playwright từng viewport (390, 768, 1280, WebKit), 3 pha có reset DB: auth, teacher, student, publish-flow, sources-refresh 6 đến 7/7; habit, habit-panel, upload, personalization 5/5; `insights.spec.ts` (học sinh hỏi và làm sai, giáo viên thấy nhóm câu hỏi ẩn danh, tóm tắt, bấm "AI gợi ý bài tập thêm" sang trang soạn) 4/4. Ảnh: `.agents/screens-insights/`.

## Env mới
Không có. (Dùng `CHAT_MODE=llm` và `CHAT_DAILY_TOKEN_BUDGET` sẵn có cho "AI phân tích".)

## Rủi ro
Câu hỏi tự do có thể tự nêu danh tính; lớp nhỏ thì khó ẩn danh (ghi ở threat model H-21). Chưa thử "AI phân tích" với model thật. Cache phân tích mất khi restart.
