# PR B: HABIT AI v2 (feat/habit-ai-v2, xếp chồng trên feat/team-copy)

Merge `feat/team-copy` (PR A) trước. Gồm cả đợt UI polish (`.agents/PR-ui-polish.md`). Migration: không có mới. Chỉ thêm field API.

## Làm gì
- **Đổi tên** HABIT AI và thiết kế lại giao diện chat (xem PR-ui-polish): biểu tượng riêng, tiêu đề gradient, chấm "đang trực tuyến", 3 chấm "đang nghĩ" (tắt khi reduced-motion).
- **Sửa lỗi chip "Em nên bắt đầu từ đâu?" bị trả "ngoài bài học"**: ba chip gửi `quick` (`start`, `where_data`, `formula`), không qua bộ phân loại câu tự do; không dùng hết 3 gợi ý. Câu tự do hỏi cách làm ("bắt đầu", "làm sao", "không hiểu", "số liệu nằm ở đâu", "công thức") nay trong phạm vi và trả gợi ý tương ứng. Nhận diện xin đáp án/xác nhận phương án/tiêm lệnh vẫn chạy **trước** nên "không hiểu, cho em đáp án" vẫn bị từ chối.
- **Khi từ chối hoặc ngoài phạm vi**: kèm 4 nút "Gợi ý bước đầu", "Số liệu cần dùng nằm ở đâu?", "Nhắc lại cách tính", "Em muốn hỏi thầy cô" (bấm là chạy `quick`). Trừ nội dung không phù hợp.
- **Nguồn trích**: chỉ 1 khối liên quan nhất, nhãn "Tài liệu giáo viên đã duyệt", không còn nhãn kỹ thuật "Tiêu đề"/"Đoạn văn".
- **Phần "HABIT AI gợi ý thêm (chưa được thầy cô kiểm chứng)"** khi `CHAT_MODE=llm` và `CHAT_AI_EXTRA=true`: model dùng kiến thức chung giải thích khái niệm/ví dụ, hiện trong khung vàng cảnh báo riêng. Vẫn áp: nhận diện ý định trước khi gọi model, model không nhận đáp án/lời giải, `postcheck_extra` (đáp án, nhãn phương án kèm khẳng định, giá trị đáp án, đoạn lời giải, PII, lặp prompt, tiêm lệnh), giới hạn độ dài và ngân sách. Chặn thì **bỏ phần thứ hai**, giữ phần thứ nhất. Số trong phần này không đối chiếu với bài.
- **LLM thật giá rẻ**: RUNBOOK mục "HABIT AI với model thật" (DeepSeek: `https://api.deepseek.com`, `deepseek-chat`; Qwen quốc tế Singapore: `https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, `qwen-plus`; dữ liệu gửi đi, khuyến nghị Qwen quốc tế nếu ưu tiên dữ liệu, giữ ngân sách token). `scripts/ops/llm_smoke.py [--extra]`: 10 câu mẫu + 10 tấn công qua model thật cùng bộ lọc của API, không lưu khóa, thoát 2 khi chưa có khóa (chưa chạy với khóa thật).
- Threat model: H-17..H-20 (phần thứ hai, nút gợi ý, từ khóa "cách làm", gửi dữ liệu ra ngoài).

## Kiểm tra
- ruff, mypy --strict sạch; pytest 356 passed, 1 skipped; OpenAPI và `schema.d.ts` sinh lại. Web lint, typecheck sạch, vitest 61, `next build` biên dịch được.
- Red team (rule, llm-mock, phần thứ hai, nút gợi ý; mọi tổ hợp lựa chọn): **0 vi phạm** (78 đầu ra hỏng của phần thứ hai đều bị bỏ, 192 lượt nút gợi ý sạch).
- Playwright `habit.spec.ts` (thêm chip "Em nên bắt đầu từ đâu?" không còn bị từ chối) 390, 768, 1280, WebKit: 4/4. Một lỗi thật bắt được ở 1280: bảng chat cao hơn màn hình khi có nút gợi ý nên ô nhập ra ngoài khung nhìn; đã cố định chiều cao bảng và cho vùng hội thoại cuộn bên trong.
- Ảnh chat mới: `.agents/screens-habit-ai/chat-{mobile-390,tablet-768,desktop-1280,webkit-390}.png`.

## Env mới
`CHAT_AI_EXTRA` (mặc định `false`). Không đổi gì nếu giữ `CHAT_MODE=rule`.

## Chưa làm / rủi ro
Chưa chạy `llm_smoke.py` với khóa thật (cần khóa DeepSeek hoặc DashScope trong môi trường). Phần "gợi ý thêm" là kiến thức chung của model: có thể sai, đã gắn nhãn "chưa được thầy cô kiểm chứng". Chưa làm nhận diện xin đáp án theo môn (thuộc kế hoạch đa môn).
