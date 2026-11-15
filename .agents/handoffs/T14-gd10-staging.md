# Handoff: T14 — GĐ10 Docker staging/prod, RUNBOOK, smoke

Status: `in_review` (chưa chạy được cổng, xem dưới)
Date: 2026-11-15 · nhánh `feat/backend-v2` (đã merge `feat/web-frontend` của Thiện, không xung đột)

## Outcome
Compose staging/prod build được api+web tại chỗ, api tự migrate/seed khi khởi động, có healthcheck, service `backup` (profile), `scripts/smoke.py` chạy toàn luồng GV→HS→thu hồi, `docs/operations/RUNBOOK.md`.

## Changed files
- `apps/api/Dockerfile`, `apps/api/docker-entrypoint.sh` — image giờ có alembic + seed; entrypoint `alembic upgrade head`, seed nếu `SEED_DEMO=true`.
- `infra/compose.{staging,prod}.yml` — `build:`, healthcheck api, caddy chờ api healthy, service `backup` (profile `backup`).
- `infra/.env.{staging,prod}.example` — `APP_ENV`, `COOKIE_SECURE`, `FRONTEND_ORIGIN`, `SEED_DEMO`, `SEED_PASSWORD`.
- `scripts/smoke.py`, `docs/operations/RUNBOOK.md`.

## Verification evidence
- `docker compose ... --profile backup config -q` sạch (staging); `py_compile` smoke.py, `sh -n` entrypoint sạch.
- 15/11: `pytest` đầy đủ với Postgres dev: 162 passed (AT-01..14, PR-08, IDOR); ruff + mypy --strict sạch.
- 15/11: `scripts/smoke.py` → `SMOKE OK` với API chạy native (uvicorn) trên Postgres dev. Phát hiện và sửa: nguồn dán text không có bảng nên không sinh câu hỏi → `parse_text` nay nhận khối `|`/tab ≥2 dòng là bảng (TABLE_CELL).
- Thêm `OpenAICompatibleProvider` (`LLM_PROVIDER=openai_compatible` + `LLM_BASE_URL/API_KEY/MODEL`), test bằng server giả. **Chưa gọi LLM thật.** Nội dung nguồn của GV sẽ gửi tới nhà cung cấp đó; cần xác nhận trước khi bật.
- **Chưa chạy:** `docker compose up` đầy đủ (build web bị dừng vì thiếu RAM; giao cho job CI `stack`), chưa build image web.

## Còn nợ / rủi ro
- Cổng GĐ10 chỉ đạt khi `up --build` + `smoke.py` ra `SMOKE OK` trên máy sạch/CI.
- `backup` cần `infra/backup-recipients.txt` (age) nên mặc định tắt; `apk add age` lúc khởi động cần mạng.
- `smoke.py` giả định MockProvider cho nguồn text sinh bản nháp không có BLOCKER (test hiện có chỉ dùng DOCX có bảng); sai thì bước `publish-check` báo.
- Chưa có DOCX malware scan (nợ từ GĐ5).
