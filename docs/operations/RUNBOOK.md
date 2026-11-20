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

## Cloud demo (Vercel + Render + Neon) — vận hành
Quyết định và giới hạn: `docs/adr/ADR-0011-cloud-demo-deploy.md`; cài đặt và biến môi trường: `docs/operations/DEPLOY-cloud.md`; bảo mật: `docs/security/SECURITY-REVIEW-2026-11-20.md`; buổi khảo sát: `docs/survey/CHECKLIST-BUOI-TEST.md`.

**Auto-deploy Render (quan trọng).** Mã API chỉ lên cloud khi Render **build commit mới**. Đổi biến môi trường chỉ **khởi động lại bản đã build** (không lấy commit mới). Vào Render → `preclass-api` → Settings → Build & Deploy → *Auto-Deploy = On Commit* (đã gặp sự cố vì chỗ này: mã `seed.survey` mới không chạy sau khi merge). Nếu tắt: sau mỗi merge bấm **Manual Deploy → Deploy latest commit**. Vercel (web) tự deploy khi merge vào `main`; biến `NEXT_PUBLIC_*` và `API_ORIGIN` chỉ có hiệu lực khi **Redeploy** (bỏ tick build cache).

**Biết commit nào đang chạy.** `curl https://pre-class-ai.vercel.app/v1/health` trả `{"status":"ok","commit":"<7 ký tự>"}` (Render điền `RENDER_GIT_COMMIT`; local trả `dev`). So với `git log origin/main --format=%h -1`; khác nhau nghĩa là chưa deploy. Log khởi động Render phải có `survey class KS: assignments added: …` và `e2e class: …` (thiếu: `seed.survey` chưa chạy). `WARNING: … NOT created` nghĩa là thiếu hoặc ngắn (< 12 ký tự) biến `SEED_*_PASSWORD` hoặc `E2E_STUDENT_PASSWORD`; API vẫn chạy.

**Khởi động (Start Command Render).** `export PYTHONPATH=. && python -m alembic upgrade head && python -m seed.seed --if-empty && python -m seed.accounts && python -m seed.survey && python -m uvicorn app.main:app …` (xem `render.yaml`). Blueprint **không** tự cập nhật lệnh này trong dashboard: sửa tay ở Settings khi `render.yaml` đổi.

**Lớp khảo sát và lớp E2E.** Khách chỉ vào lớp `KS`; `seed.survey` giao cho KS **chỉ bài seed đã xuất bản** và gỡ các assignment khác chưa có bài làm. E2E dùng lớp riêng `E2E` (học sinh `E2E-1`, mật khẩu `E2E_STUDENT_PASSWORD`), bài có tiền tố `[E2E]`, và teardown rút hết sau mỗi lần chạy (cần `E2E_TEACHER_PASSWORD`). Chạy E2E cloud (PowerShell riêng, mật khẩu không vào chat hay tệp):
`cd apps\web; $env:E2E_TEACHER_PASSWORD="…"; $env:E2E_STUDENT_PASSWORD="…"; $env:E2E_BASE_URL="https://pre-class-ai.vercel.app"; npx playwright test -c playwright.release.config.ts`.
Sau khi chạy, khách mới phải vẫn chỉ thấy bài seed. **Không chạy E2E trong giờ khảo sát.**

**Backup trước khi reset (hai lớp).**
1. *Neon branch (nhanh, khuyến nghị):* Neon Console → project → Branches → **Create branch** từ `production`, đặt tên `backup-before-reset-YYYYMMDD`. Branch là bản sao tức thời (copy-on-write). Khôi phục: Branches → chọn branch → *Restore*, hoặc đổi `DATABASE_URL` trên Render sang chuỗi của branch đó rồi Manual Deploy.
2. *pg_dump ra tệp:* `cd apps\api; $env:DATABASE_URL="<Neon direct>"; uv run python ..\..\scripts\ops\backup_demo_db.py` (dùng Docker `infra-postgres-1`; tệp lưu ngoài repo, mặc định `~/preclass-backups`, không commit). Khôi phục: `docker exec -i infra-postgres-1 pg_restore -U preclass -d <db_tạm> < tệp.dump`.

**Reset DB demo (xóa mọi dữ liệu).** PowerShell riêng, trong `apps\api`: đặt `DATABASE_URL` (Neon **direct**), `APP_ENV=demo`, `FRONTEND_ORIGIN`, ba `SEED_*_PASSWORD` **giống hệt Render** và `E2E_STUDENT_PASSWORD`, rồi `uv run python ..\..\scripts\ops\reset_demo_db.py` (gõ `RESET`). Script từ chối trước khi xóa nếu thiếu mật khẩu; sau khi chạy nó seed lại tài khoản, bài mẫu, lớp KS và E2E. Kiểm sau reset: `/v1/health`, `guestEnabled`, khách mới chỉ thấy bài seed, GV đăng nhập được.

**Đổi mật khẩu.** `scripts/ops/rotate_passwords.py` (đặt `SEED_*_PASSWORD` mới ở Render **và** trong lệnh; nó thu hồi mọi phiên). Học sinh seed không đăng nhập bằng mật khẩu (chỉ khách) trừ khi đặt `SEED_STUDENT_PASSWORD`.

**Sự cố cloud thường gặp**
| Hiện tượng | Nguyên nhân / cách xử lý |
|---|---|
| `/login` hiện "Máy chủ đang khởi động" | Render ngủ hoặc đang khởi động; chờ 60 giây, bấm Thử lại. Mọi request có timeout 60 giây, config 15 giây (không còn spinner vô hạn) |
| UptimeRobot Down với phản hồi nhanh | Trước đây HEAD bị 405; đã sửa (`HEAD /v1/health` 200). Kiểm bằng `curl -I` |
| Vercel `DNS_HOSTNAME_RESOLVED_PRIVATE` / build lỗi `API_ORIGIN` | Thiếu hoặc sai `API_ORIGIN` (cả Production và Preview); build có guard |
| Đăng nhập 403 CSRF | `FRONTEND_ORIGIN` trên Render phải đúng `https://pre-class-ai.vercel.app` |
| `/docs` 401/404 | `DOCS_ACCESS=staff` (cần đăng nhập GV/admin) hoặc `off` |
| Khách 429 / 503 | `GUEST_CREATE_PER_HOUR` (mỗi IP) / `GUEST_MAX_ACTIVE`; xem `/v1/admin/survey/stats` |
| Khách thấy bài lạ | Render chưa chạy `seed.survey` mới; xem "Biết commit nào đang chạy" |
