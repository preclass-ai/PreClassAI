# Deploy cloud demo (Vercel + Render + Neon)

Quyết định và giới hạn: `docs/adr/ADR-0011-cloud-demo-deploy.md`. Chỉ dữ liệu minh họa, không dữ liệu học sinh thật.

## Thứ tự

1. **Neon:** project `preclass`, AWS Singapore, Postgres 16. Lấy chuỗi **Direct** (host không có `-pooler`) dạng `postgresql://…?sslmode=require`. App tự đổi scheme sang asyncpg và `sslmode` → `ssl`.
2. **Render:** New → Blueprint → repo, nhánh `main` (đọc `render.yaml`). Nhập `DATABASE_URL` (chuỗi Neon) và `FRONTEND_ORIGIN` (`https://pre-class-ai.vercel.app`). Start command tự `alembic upgrade head`, seed nếu DB trống, rồi chạy uvicorn.
3. **Vercel:** import repo, tên project `preclass-ai`, Root Directory `apps/web`, biến **Environment `API_ORIGIN`** = URL Render (vd `https://preclass-api.onrender.com`, không có `/` cuối). Vercel tự dùng `pnpm-lock.yaml` ở gốc repo (workspace `@preclass/api-client`). Build không dùng `standalone` khi `VERCEL=1`.
4. Nếu URL Vercel khác `pre-class-ai.vercel.app`: sửa `FRONTEND_ORIGIN` trên Render và redeploy.
5. UptimeRobot: HTTP monitor 5 phút tới `https://<vercel>/v1/health`.

## Biến môi trường API (Render)

| Biến | Giá trị |
|---|---|
| `DATABASE_URL` | chuỗi Neon direct (secret, nhập tay) |
| `FRONTEND_ORIGIN` | URL Vercel |
| `APP_ENV` | `demo` (seed từ chối khi `production`) |
| `LLM_PROVIDER` | `mock` |
| `DB_POOL_SIZE` / `DB_MAX_OVERFLOW` / `DB_POOL_RECYCLE` | `5` / `0` / `300` |
| `SESSION_SECRET` | Render tự sinh |
| `PYTHON_VERSION` | `3.12.8` (Render cần số phiên bản đầy đủ) |
| `SEED_TEACHER_PASSWORD`, `SEED_REVIEWER_PASSWORD`, `SEED_ADMIN_PASSWORD` | ≥ 12 ký tự mỗi biến (secret, nhập tay). Thiếu: tài khoản demo không được tạo, log cảnh báo, API vẫn chạy |
| `SEED_STUDENT_PASSWORD` | tùy chọn; không đặt = HS seed không đăng nhập bằng mật khẩu (chỉ khách) |
| `GUEST_ACCESS_ENABLED`, `GUEST_CLASS_CODE`, `GUEST_CREATE_PER_IP` | `true`, `KS`, `200` mỗi 10 phút theo IP (một lớp dùng chung Wi-Fi; mặc định cũng là 200) |
| `DOCS_ACCESS` | `staff` (khuyến nghị cho demo), `off` cho production |

Nếu bắt buộc dùng chuỗi pooled (`-pooler`), app tự tắt prepared-statement cache của asyncpg; nhưng migration vẫn nên chạy bằng chuỗi direct.

## Rollback

- Render hoặc Vercel: Deployments → chọn commit trước → Redeploy / Promote.
- Schema chỉ tiến (migration SQL không có downgrade): rollback code qua migration mới thì khôi phục DB.
- **Đặt lại DB demo:** Neon Console → Branches → Restore (về mốc thời gian), hoặc chạy `scripts/ops/reset_demo_db.py` (xóa schema, migrate, seed; hỏi gõ `RESET`).
- Đổi DB: tạo project/branch Neon mới, sửa `DATABASE_URL` trên Render, redeploy (tự migrate và seed).

## Kiểm tra sau deploy

`curl https://<vercel>/v1/health`, mở `/docs`, đăng nhập GV/HS demo. Cookie phải `Secure; HttpOnly; SameSite=Lax`. Chạy `scripts/smoke.py` trỏ URL cloud.

## Chẩn đoán nhanh

- Vercel trả `X-Vercel-Error: DNS_HOSTNAME_RESOLVED_PRIVATE` ở `/v1/*`: `API_ORIGIN` thiếu hoặc là localhost khi build. Từ nay build fail rõ ràng; sửa biến rồi Redeploy **không dùng build cache**.
- Đăng nhập 403 `CSRF`: `FRONTEND_ORIGIN` trên Render phải đúng `https://pre-class-ai.vercel.app`. Log Render có dòng `CSRF rejected: … origin=… expected=…` (không có cookie/token).
- API với `APP_ENV=demo|production` từ chối khởi động nếu `FRONTEND_ORIGIN` không phải https công khai.
