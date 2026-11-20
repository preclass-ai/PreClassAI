# RUNBOOK — staging/prod (GĐ10)

Stack: `postgres` + `api` (FastAPI) + `web` (Next.js) + `caddy` (TLS, `/v1/*` → api, còn lại → web) + `backup` (tùy chọn). Chi tiết bổ sung: `deployment-runbook.md`, `backup-restore-runbook.md`, `monitoring-runbook.md`.

## Chạy staging trên máy sạch

```bash
cd infra
cp .env.staging.example .env.staging     # đổi POSTGRES_PASSWORD (và trong DATABASE_URL), SESSION_SECRET, SEED_PASSWORD, APP_HOSTNAME, FRONTEND_ORIGIN
docker compose -f compose.staging.yml up -d --build   # build api+web tại chỗ; api tự migrate, SEED_DEMO=true thì seed
python ../scripts/smoke.py --base https://localhost --insecure --password "<SEED_PASSWORD>"   # in "SMOKE OK"
```

- `FRONTEND_ORIGIN` phải bằng `https://$APP_HOSTNAME` (kiểm tra Origin chống CSRF của API); sai → mọi POST trả 403 `CSRF`.
- `APP_HOSTNAME=localhost` → Caddy dùng CA nội bộ (trình duyệt cảnh báo; smoke dùng `--insecure`). Tên miền thật → Let's Encrypt, cần cổng 80/443 mở.
- Chỉ staging có seed (`SEED_DEMO=true`, `APP_ENV=staging`). **Prod: `APP_ENV=production`, `SEED_DEMO=false`**; seed từ chối chạy khi `APP_ENV=production`. Tài khoản seed: `gv.dia@preclass.local`, `HS10-01..15`, `HS11-01..15`, `admin@preclass.local`.
- Prod dùng image từ registry: `IMAGE_TAG=<sha> docker compose -f compose.prod.yml pull && ... up -d` (bỏ `--build`).
- `smoke.py` ghi dữ liệu thật (nguồn, bài, bài giao) → **chỉ chạy trên staging**.

## Backup / restore

- Bật: tạo `infra/backup-recipients.txt` (khóa công khai `age`, giữ khóa bí mật ngoài server), rồi `docker compose -f compose.staging.yml --profile backup up -d backup`. Mỗi 24 giờ: `pg_dump | gzip | age` vào volume `backups-<env>`, xóa file > 14 ngày.
- Restore: `infra/restore.sh` (xem `backup-restore-runbook.md`). **Diễn tập restore trên staging trước khi dùng prod.**
- Backup chưa bật = chưa có bản sao nào của dữ liệu học sinh.

## Sự cố thường gặp

| Triệu chứng | Xử lý |
|---|---|
| `api` unhealthy | `docker compose logs api`: lỗi migrate (DB chưa sẵn sàng/mật khẩu lệch giữa `POSTGRES_PASSWORD` và `DATABASE_URL`) |
| Đăng nhập OK nhưng thao tác 403 `CSRF` | `FRONTEND_ORIGIN` ≠ origin trình duyệt |
| Cookie không giữ trên http | `COOKIE_SECURE=true` cần https; chỉ đặt `false` cho dev |
| Generate trả 503 `AI_DISABLED` | `AI_ENABLED=false`; phần còn lại vẫn chạy |
| Job generate kẹt | restart `api`: job RUNNING chuyển FAILED, tạo lại |
| Giới hạn đăng nhập sai (rate limit) lệch/mất | chạy API với `--workers 1`: bộ đếm nằm trong bộ nhớ từng tiến trình; không tăng worker khi chưa chuyển sang kho dùng chung |
| Chạy `up` lỗi cổng 80/443 | cổng bị chiếm; dừng dịch vụ đang dùng |

## Rollback

`IMAGE_TAG=<tag cũ> docker compose -f compose.prod.yml up -d`. Migration chỉ tiến (`alembic upgrade head` lúc khởi động); lùi schema cần `alembic downgrade` thủ công **sau khi backup**.

## Demo preview trên laptop (19/11)
- Khởi động: bật Docker Desktop → `PYTHONPATH=. uv run python -m alembic upgrade head && uv run python -m seed.seed` (trong `apps/api`, nếu DB trống) → `cd apps/web && corepack pnpm@10 build` (EPERM ở bước standalone là chấp nhận được) → `powershell -File scripts\ops\preview.ps1`. URL mới ở `.agents/PREVIEW_URL.md`, basic auth ở `apps/api/data/preview-credentials.txt`. Tắt: `scripts\ops\preview-stop.ps1`.
- Khởi động lại sau khi tunnel chết: `preview-stop.ps1` rồi `preview.ps1` (URL đổi). Không build lại web nếu mã không đổi.
- Quay lui: `git checkout pre-merge-2026-11-19` (hoặc revert merge PR #8), build lại web, khởi động lại preview.
- Khôi phục DB từ backup: `docker exec -i infra-postgres-1 psql -U preclass -d preclass -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"` rồi `docker exec -i infra-postgres-1 psql -U preclass -d preclass < apps/api/data/backup/predeploy-1911.sql`. Thử khôi phục vào DB tạm `preclass_restore_check` trước. Chỉ đụng database `preclass`, không xoá volume.
- Reset về seed sạch: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` trên `preclass`, rồi migrate + seed như trên.

## Habit (chat và thói quen học)

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `CHAT_ENABLED` | `false` | Bật Habit. Tắt: route 404, UI ẩn, hệ thống như cũ. Đổi cần restart API. |
| `CHAT_MODE` | `rule` | `rule` = 0đ, không gọi LLM. `llm` = rule vẫn quyết định và hậu kiểm, LLM chỉ viết lại. |
| `CHAT_LLM_BASE_URL`, `CHAT_LLM_API_KEY`, `CHAT_LLM_MODEL` | rỗng | Chỉ khi `llm`. Thiếu một biến thì tự dùng rule. Khóa đặt trên Render, không commit. |
| `CHAT_MAX_OUTPUT_TOKENS` / `CHAT_DAILY_TOKEN_BUDGET` | 220 / 300000 | Hết ngân sách ngày thì tự dùng rule (học sinh không thấy lỗi). |
| `CHAT_MAX_PER_DAY_PER_STUDENT` / `CHAT_MAX_PER_ITEM` | 30 / 6 | Quá hạn mức → 429 thân thiện. |
| `HABIT_DAILY_GOAL` | 3 | Mục tiêu câu/ngày. |

Giá trị đề xuất trên Render cho đợt thử: `CHAT_ENABLED=true`, `CHAT_MODE=rule`, còn lại mặc định. Tắt khẩn cấp: `CHAT_ENABLED=false` rồi restart. Cần migration `alembic upgrade head` (0003) trước khi bật.

Xem tokens và số lần bị chặn: đăng nhập ADMIN rồi `GET /v1/admin/survey/stats` (`chatTotal, chatFallbackRate, chatBlocked, chatTokensIn/Out`). Red team trước khi bật `llm`: `cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/habit_redteam.py` (0 vi phạm). Giữ uvicorn `--workers 1`: cache và giới hạn dùng bộ nhớ một tiến trình.
