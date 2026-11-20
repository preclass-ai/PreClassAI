# PR: Habit — trợ lý học từng bước (feat/habit-chat)

Mặc định TẮT (`CHAT_ENABLED=false`): không đổi gì cho hệ thống hiện tại. An toàn: `docs/security/THREAT-MODEL-habit.md`. ADR: `docs/adr/ADR-0012-habit-chat.md`. UI: `docs/ui/HABIT-DESIGN.md`.

## Làm gì
- API: `GET /v1/student/assignments/{id}/habit`, `POST .../chat` (hint 1→3 / ask / explain), `chatEnabled` ở `/auth/config`, CSV khảo sát + stats thêm số đếm Habit. Migration 0003 chỉ thêm 3 bảng (`chat_message` append-only).
- Rule engine 0đ (`app/habit/rules.py`); chế độ `llm` tùy chọn có hậu kiểm (`app/habit/llm.py`), mặc định không bật.
- FE S07: thanh Habit (streak, mục tiêu x/3, huy hiệu), thẻ Gợi ý, chat bottom-sheet/panel (chunk lazy), "Habit giải thích".

## Kiểm tra (local)
- pytest 273 passed, 1 skipped; ruff sạch; mypy --strict sạch. Web lint/typecheck sạch; vitest 46 passed; Playwright habit.spec 390/768/1280/WebKit 4/4; E2E cũ (auth/student/teacher) xanh với CHAT_ENABLED=false (1 lần flake ở mobile-390 teacher do dev server biên dịch lần đầu, chạy lại xanh).
- Red team `scripts/ops/habit_redteam.py`: 12 câu hỏi (6 bài seed) × 59 câu tấn công, rule + llm-mock, **0 vi phạm**.
- RAM API (rule): ~89 MB sau 60 lượt chat (đỉnh 151 MB). Bundle S07: JS ban đầu 122.0 → 124.4 KB gz (+2.4); chat nằm chunk lazy.
- Ảnh: `apps/web/test-results/habit/*.png` (thư mục gitignored).

## Env đề xuất trên Render
`CHAT_ENABLED=true`, `CHAT_MODE=rule`; còn lại mặc định. Chạy `alembic upgrade head` trước.

## Rủi ro / chưa làm
Xem ADR-0012 mục Hậu quả. Habit view dựng từ snapshot, không thêm trường provenance (xem DECISIONS_AGENT.md). PHIEU-KHAO-SAT nằm ở nhánh docs/proposal nên câu hỏi Habit ở `docs/CAU-HOI-KHAO-SAT-HABIT.md`. Chế độ `llm` chưa thử với model thật.
