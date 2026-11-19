# T9 backend v2 — handoff (đang làm)

Trạng thái: GĐ1–GĐ3 xong (hợp đồng v0); GĐ4 đạt một phần (auth thật; IDOR source/lesson/block/student là điều kiện cổng GĐ5/6/9). Đã làm thêm trước GĐ5: PUT sources (AT-08), packages/api-client, apps/console, /docs (Scalar), preview qua tunnel.

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

## Preview tạm trên laptop
- Bật: `powershell -File scripts\ops\preview.ps1` (postgres container → migrate+seed → uvicorn `--workers 1` → Prism → Caddy :8080 → cloudflared quick tunnel). Tắt: `scripts\ops\preview-stop.ps1` (chỉ PID do script tạo; Postgres giữ nguyên).
- Cần `winget install CaddyServer.Caddy Cloudflare.cloudflared --scope user` (đã cài).
- Basic auth: `PREVIEW_BASIC_AUTH=user:pass`, hoặc tự sinh vào `apps/api/data/preview-credentials.txt` (không commit). URL tunnel ở `.agents/PREVIEW_URL.md` (không commit) và đổi mỗi lần tunnel khởi động lại.
- Không build image Docker; log ở `apps/api/data/logs`.
- Không có `gh` trên máy: Draft PR mở thủ công, nội dung ở `.agents/handoffs/PR-backend-v2.md`.

## Phát hành demo 19/11 (từ `main` @ `41d9d71`, PR #7 + #8)
- Mốc quay lui: tag `pre-merge-2026-11-19` (= `0a03e1f`, main trước hotfix). Backup DB dev trước khi reset: `apps/api/data/backup/predeploy-1911.sql` (gitignore, đã thử khôi phục: 34 user / 8 lesson / 118 block).
- DB `preclass` đã reset về seed sạch (34 user, 6 bài, bài `dan-so-vung` đã giao 10A1). Tài khoản HS đã dùng khi kiểm thử: HS10-12 (390px), HS10-13 (1280px) — mỗi tài khoản chỉ nộp 1 lần/câu; dùng HS10-01.. cho demo thật.
- Hotfix PR #8: pool DB 10+5/10 s; duyệt khối chỉ làm mới provenance của khối đó (trước đó N² request → 429 từ tunnel, 5xx do cạn pool); retry 5xx 1 lần. Sửa FE tối thiểu, **cần Thiện review**.
- Kiểm: ruff, mypy --strict, pytest 162 pass/1 skip, web lint/typecheck/vitest 31/build; E2E Playwright qua tunnel (`apps/web/playwright.release.config.ts`).

### Lỗi còn tồn (không chặn demo)
- `scripts/ops/preview.ps1` gọi `uv run alembic` thiếu `PYTHONPATH=.` → lỗi "No module named app" khi DB trống. Cách lách: `PYTHONPATH=. uv run python -m alembic upgrade head && uv run python -m seed.seed` rồi mới chạy preview.ps1.
- S01 ở màn 1280: sau "Lưu nguồn" nguồn mới không hiện ngay trong danh sách (tải lại thì thấy); chưa rõ nguyên nhân (FE).
- S05: sau khi duyệt khối cuối, bảng kiểm xuất bản có thể báo còn khối chưa duyệt (cache); tải lại trang trước khi bấm Xuất bản. Sau hotfix #8 không tái hiện lại.
- Truy cập provenance bằng tài khoản HS trả 403 (docs ghi 404); chấp nhận cả hai.
- Lần tải đầu qua tunnel có thể ~3–11 s (khởi động lạnh).
- E2E chưa chạy đủ: luồng GV ở 768/1280 và withdraw/republish trên UI (backend có AT-12).
