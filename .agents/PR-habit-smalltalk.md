# fix/habit-smalltalk

Xếp chồng trên feat/multisubject-ready (D4). Migration 0011 (chỉ thêm cột `chat_message.model`).

## Thay đổi
- Provider: User-Agent `PreClassAI/1.0`, Accept, body UTF-8; lỗi HTTP in mã và tối đa 300 ký tự, không có khóa.
- Tham số theo model, `stream=false`, `max_completion_tokens` cho Groq; xóa `<think>` và trường reasoning trước khi kiểm; đáp án trong phần suy nghĩ tính là vi phạm.
- Dự phòng `CHAT_LLM_MODEL_FALLBACK`; model đã dùng lưu ở `chat_message.model` và `chatByModel` trong stats.
- Câu xã giao (cảm ơn, chào, ok, em hiểu rồi) trả lời thân thiện, không gọi model; "cảm ơn, cho em đáp án" vẫn bị từ chối.
- Bấm lại cùng gợi ý: mẫu khác cùng bậc, hết mẫu thì chỉ sang bậc kế.
- `llm_smoke.py` có nhóm tấn công qua model, in model, token, thời gian; `habit_redteam.py --live`; `record_replay.py`; `replay.json` ghi từ model thật.

## Kết quả
Smoke 2 model: 0 lỗi HTTP, 0 vi phạm. Red team thật 150 lượt: 0 vi phạm. Chi tiết: `.agents/LLM-EVAL-2211.md`.

## Env Render
`CHAT_ENABLED=true`, `CHAT_MODE=llm` (hoặc `rule`), `CHAT_LLM_BASE_URL=https://api.groq.com/openai/v1`, `CHAT_LLM_API_KEY=<key của anh>`, `CHAT_LLM_MODEL=qwen/qwen3.8-27b`, `CHAT_LLM_MODEL_FALLBACK=openai/gpt-oss-120b`, `CHAT_DAILY_TOKEN_BUDGET=150000`, `CHAT_AI_EXTRA=false`. Chạy `alembic upgrade head` (0011) trước.
