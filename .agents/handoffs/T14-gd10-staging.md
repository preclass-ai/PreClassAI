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
- **Chưa chạy:** `docker compose up` và `smoke.py` (Docker daemon không chạy trên máy này lúc làm), chưa build image api/web.

## Còn nợ / rủi ro
- Cổng GĐ10 chỉ đạt khi `up --build` + `smoke.py` ra `SMOKE OK` trên máy sạch/CI.
- `backup` cần `infra/backup-recipients.txt` (age) nên mặc định tắt; `apk add age` lúc khởi động cần mạng.
- `smoke.py` giả định MockProvider cho nguồn text sinh bản nháp không có BLOCKER (test hiện có chỉ dùng DOCX có bảng); sai thì bước `publish-check` báo.
- Chưa có DOCX malware scan (nợ từ GĐ5).
