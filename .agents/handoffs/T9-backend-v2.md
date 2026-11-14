# T9 backend v2 — handoff (đang làm)

Trạng thái: GĐ1–GĐ3 xong (hợp đồng v0). GĐ4 (auth thật) đang làm.

## Chạy local (Windows, RAM thấp)
1. `docker compose -f infra/compose.dev.yml up -d postgres` (không build api, không bật web/caddy). Postgres giới hạn 512M.
2. Trong `apps/api`: `uv sync`, rồi `DATABASE_URL=postgresql+asyncpg://preclass:preclass@localhost:5432/preclass uv run alembic upgrade head && uv run python -m seed.seed`.
3. `uv run uvicorn app.main:app` (API native). Test: `uv run pytest` (đọc `TEST_DATABASE_URL`, mặc định `.../preclass_test`; test `db` tự skip nếu không có Postgres và **tự drop/tạo lại DB `*_test`**).
4. Xuất hợp đồng: `uv run python -m scripts.export_openapi`; CI so khớp file đã commit.

## Còn nợ / lưu ý
- Image `api` chưa build trên máy này (RAM); build ở CI/staging hoặc GĐ10.
- `.claude/settings.json` chưa áp (Khải áp tay, xem D-001 §5.2).
- Chưa có malware scan cho DOCX (sẽ ghi lại ở GĐ5).
- Seed dùng mật khẩu dev `preclass-demo`; đặt `SEED_PASSWORD` ở mọi nơi khác.
