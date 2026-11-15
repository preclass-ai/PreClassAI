# Handoff: T14 — GĐ10 Docker staging/prod, RUNBOOK, smoke

Status: `done` (cổng GĐ10 đạt local 16/11; job CI `stack` chạy sau push)
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
- 16/11: `compose.staging.yml --profile backup up -d --build` (Docker Desktop, 6 GB) → 5 service chạy, api healthy; `smoke.py --base https://localhost --insecure` → `SMOKE OK`. Sửa 2 lỗi build: pnpm mới bỏ qua build script esbuild (ghim `pnpm@10` trong `apps/web/Dockerfile`); alembic không thấy package `app` (`PYTHONPATH=/app` trong `apps/api/Dockerfile`). `docker compose` cần `--env-file .env.staging` để nội suy `IMAGE_TAG`.
- 16/11: backup đã kiểm chứng: `backup.sh` tạo `.sql.gz.age`; `restore.sh` giải mã vào DB `restore_check` → `app_user=34, content_block=114, audit_log=5` khớp DB gốc (khóa age tạm, đã xóa). Trên Windows `backup.sh` phải là LF.

## Còn nợ / rủi ro
- Cổng GĐ10 chỉ đạt khi `up --build` + `smoke.py` ra `SMOKE OK` trên máy sạch/CI.
- `backup` cần `infra/backup-recipients.txt` (age) nên mặc định tắt; `apk add age` lúc khởi động cần mạng.
- `smoke.py` giả định MockProvider cho nguồn text sinh bản nháp không có BLOCKER (test hiện có chỉ dùng DOCX có bảng); sai thì bước `publish-check` báo.
- Chưa có DOCX malware scan (nợ từ GĐ5).
