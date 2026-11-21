# PR: sửa bảng HABIT AI, Groq, tên model DeepSeek (fix/habit-panel-ui)

Base: `main` (6e2ac32) cộng commit `267dbfa` (HABIT AI v2) mà main **chưa có**: PR #32 đã merge khi nhánh mới ở `971111f`, nên bản chạy trên main vẫn gửi chip như câu tự do (xem mục A). Nhánh này chứa `267dbfa`, gộp main mới nhất.

## A. Lỗi chip "Em nên bắt đầu từ đâu?" trả "ngoài bài học": nguyên nhân là chưa triển khai, không phải lỗi mới
- `https://pre-class-ai.vercel.app/v1/health` trả `commit: e4f1604` (22/11): Render đang chạy mã **trước** cả PR #29 (post-merge), #30 (seed không lộ đáp án), #31, #32.
- Ngoài ra main (6e2ac32) chứa UI polish `971111f` nhưng **không** chứa `267dbfa` (sửa chip: gửi `quick`, câu hỏi cách làm trong phạm vi, 4 nút sau từ chối). Giao diện trong main vẫn gửi chip như câu tự do nên vẫn gặp lỗi cũ dù backend có mới.
- Cần: merge PR này vào main, rồi **deploy Render và Vercel** lên commit mới (kiểm bằng `/v1/health`).
- Đã thêm kiểm tra trên giao diện thật (`tests/e2e/habit-panel.spec.ts`): bấm đúng chip, bắt request (`action: ask`, `quick: start`, không có `message`), phản hồi không bị từ chối, không chứa "ngoài bài học" hay "Habit" riêng lẻ. Chạy ở 390, 768, 1280, WebKit. Câu từ chối dùng "HABIT AI" (test API và web).

## B. Bảng chat
- Header trang luôn rộng đủ, không bị cắt (trước đó `padding-right` đặt trên `body` thu cả header). Ở 1280 bảng đặt dưới header (top = chiều cao header), cao tới đáy, không khe hở, rộng 390px; nội dung chính co lại bằng `padding-right` trên `.content`.
- Bố cục: header bảng, dòng nhắc 1 dòng chữ nhỏ, vùng hội thoại cuộn bên trong (`flex: 1`), chip một hàng cuộn ngang có mờ hai mép, ô nhập và nút Gửi luôn ở đáy (kể cả khi có 4 nút lựa chọn sau từ chối).
- Nhỏ gọn: bong bóng 15,5px (16px ở 390), padding gọn, tối đa 85%; khung nguồn 1 khối, nhãn "Tài liệu giáo viên đã duyệt", chữ 14px, tối đa 4 dòng rồi "Xem thêm"/"Thu gọn".
- 768 và 390: bottom sheet ≤ 80dvh; trên điện thoại lắng nghe `visualViewport` để nâng sheet lên trên bàn phím và co chiều cao. **Chưa thử trên iPhone thật** (Playwright không mô phỏng bàn phím).
- Playwright `habit-panel.spec.ts` ở 1280, 768, 390, WebKit: (a) bảng trống, (b) 6 lượt gồm 3 chip, 2 câu bị từ chối, nguồn và 4 nút lựa chọn. Kiểm: header rộng đủ, bảng dưới header (1280), ô nhập và nút Gửi nằm trong khung nhìn, bảng ≤ 80% chiều cao (≤ 1100px). Ảnh: `.agents/screens-panel/`.

## C. Model LLM
RUNBOOK: Groq (`https://api.groq.com/openai/v1`, `llama-3.3-70b-versatile`; thử Qwen trên Groq như `qwen/qwen3-32b` bằng cách đổi `CHAT_LLM_MODEL` rồi chạy smoke; gói miễn phí khoảng 30 yêu cầu mỗi phút, vượt thì tự về luật), DeepSeek đổi thành `deepseek-flash` (tên cũ `deepseek-chat`/`deepseek-reasoner` đã bị DeepSeek ngừng, theo api-docs.deepseek.com; không bật suy luận). `llm_smoke.py` giãn cách theo `LLM_SMOKE_RPM` (mặc định 25) nên chạy được với Groq; đã kiểm bằng một máy chủ giả cùng dạng Groq (0 vi phạm, thoát 0); chưa chạy với khóa thật.

## Kiểm tra
ruff, mypy --strict sạch; pytest 356 passed, 1 skipped; OpenAPI không đổi; web lint, typecheck sạch, vitest 61. Playwright: habit-panel 4/4 (390, 768, 1280, WebKit), habit.spec 4/4, personalization + student 390/768/1280 xanh.
