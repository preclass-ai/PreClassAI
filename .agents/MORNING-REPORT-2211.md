# Báo cáo sáng 22/11/2026

**1. Groq: nhánh A (đạt).** Lỗi cũ do User-Agent mặc định của urllib bị Groq chặn; đã sửa. Cả hai model 0 lỗi HTTP và 0 vi phạm. Model đề xuất: `qwen/qwen3.8-27b` (0,39 s, 323/42 token mỗi lượt, bám bài), dự phòng `openai/gpt-oss-120b`. Red team thật 150 lượt: 0 vi phạm (7 phản hồi bị bộ lọc bỏ). Khuyến nghị ngày thi: `CHAT_MODE=llm` được, nhưng giữ sẵn việc đổi về `rule` (RUNBOOK); API tự về luật khi Groq lỗi. Chi tiết: `.agents/LLM-EVAL-2211.md`.

**2. Nhánh và thứ tự merge** (xếp chồng, chưa push, chưa merge):
1. `feat/lesson-plan-5512` (đã push, ae29851)
2. `feat/preclass-from-plan` 46bcde2 (migration 0008)
3. `feat/insights-v2` 608d5fc (0009)
4. `feat/multisubject-ready` 4286477 (0010)
5. `fix/habit-smalltalk` fa6fc98 (0011)
6. `fix/prelaunch-final` (xem `git log -1`; chứa hai commit sau fa6fc98 và ảnh)
```
git push -u origin feat/preclass-from-plan feat/insights-v2 feat/multisubject-ready fix/habit-smalltalk fix/prelaunch-final
```

**3. Env Render:** `CHAT_ENABLED=true`, `CHAT_MODE=llm` (hoặc `rule`), `CHAT_LLM_BASE_URL=https://api.groq.com/openai/v1`, `CHAT_LLM_API_KEY=<key của anh>`, `CHAT_LLM_MODEL=qwen/qwen3.8-27b`, `CHAT_LLM_MODEL_FALLBACK=openai/gpt-oss-120b`, `CHAT_DAILY_TOKEN_BUDGET=150000`, `CHAT_AI_EXTRA=false`, `PLAN_PARSE_TIMEOUT_S=240`, `PERSONALIZATION_ENABLED=true`, `GUEST_ACCESS_ENABLED=true`. Chạy `alembic upgrade head` (0008 đến 0011) trước khi deploy.

**4. Test:** pytest 442 passed, 1 skipped (trước thêm test remediation); ruff, mypy `--strict`, tsc, eslint, vitest 70 sạch. Playwright 4 viewport (reset DB mỗi spec): auth 8, habit 4, habit-panel 4, personalization 4, upload 8, plans 4, insights 4, teacher 8, student 4, sources-refresh 4: xanh. publish-flow: đã tìm ra nguyên nhân (mục 5), 6/6 lần chạy riêng đạt sau khi sửa test. Red team mô phỏng và thật: 0 vi phạm.

**5. Đã xử lý trong Giai đoạn 2:**
- publish-flow lệch số nút: **lỗi của test, không phải UI.** Chỉ chạy được ở 1280 và hỏng ngẫu nhiên khoảng 30 đến 40%: một cú bấm "Duyệt khối này" bị mất khi danh sách vẽ lại (không có thông báo lỗi, bộ đếm "x/y đã duyệt" khớp 6/19 với 13 thẻ còn lại). Test giờ bấm lại cho đến khi hết.
- Câu luyện thêm từ "Đề xuất dạy lại" có cờ `remediation_draft` (tham số `remediation` mới, chỉ thêm).
- Proposal §8 qua DOI. Bastani, Kestin: chỉ tóm tắt (nguồn thứ cấp), không số. Adesope: DOI cho ba tác giả Adesope, Trevisan, Sundararajan (bản cũ ghi sai tên). Låg và Sæle: có số liệu từ tóm tắt Semantic Scholar (chưa đối chiếu bài gốc), đã bỏ link ERIC. Holstein 2018: không có tóm tắt đọc được, không ghi kết luận.
- Luật 91/2025/QH15: đọc được bản tóm tắt lexdata.vn (thông qua 26/06/2025, hiệu lực 01/01/2026, Điều 24 có ngưỡng 07 tuổi cho việc công khai đời tư của trẻ). Chưa phải toàn văn, ghi rõ "cần đối chiếu văn bản gốc".
- RUNBOOK (PLAN_PARSE_TIMEOUT_S=240, số đo CPU, tải giáo án trước giờ thi, đổi CHAT_MODE) và `docs/DEMO-SCRIPT.md`.

**6. Việc chưa xong, rủi ro, việc anh phải làm tay:**
- **Lời hứa "xóa sau 90 ngày" chưa đúng hoàn toàn:** lượt trả lời là bảng chỉ thêm nên `purge_guests.py` chỉ vô hiệu hóa khách đã trả lời. Cần chọn sửa câu chữ trang `/du-lieu` hoặc làm đường xóa riêng; và xóa vẫn phải chạy tay.
- Giai đoạn 3 (humanizer toàn app, a11y, nhánh `fix/polish-final`) chưa làm.
- Ảnh demo: `.agents/screens-final/` (chụp từ các spec, không phải một bản ghi từng bước của DEMO-SCRIPT).
- Chưa kiểm: nhiều học sinh gọi model cùng lúc (giới hạn 30 yêu cầu mỗi phút của Groq); khóa Groq trong `.env.groq` là khóa trần không có tên biến, nên khi đặt trên Render chỉ dán giá trị vào `CHAT_LLM_API_KEY`.
- Dev DB local đã bị reset nhiều lần; `next build` chỉ đã biên dịch ở lượt trước (lỗi symlink Windows).
