# Handoff: T15 — Cloud demo + khảo sát ẩn danh (Vercel + Render + Neon)

Status: `done`
Owner/harness: Claude Code (Sonnet 5.5) cùng Khải
Date: 2026-11-20

## Outcome

- Web `https://pre-class-ai.vercel.app` (Vercel) → API Render (Singapore) → Neon Postgres 16 (Singapore), một origin qua rewrite `/v1`.
- Khách ẩn danh (`POST /v1/auth/guest`, `/resume`, mã `KS-XXXX`), lớp khảo sát `KS` chỉ có bài seed; link/QR `/thu?bai=dan-so-vung`; export CSV `GET /v1/admin/survey/export.csv`.
- Bảo mật: mật khẩu seed theo vai trò từ biến môi trường (không còn mặc định trên cloud), rotate script, khóa đăng nhập admin 3 lần, audit thao tác admin, CSP + HSTS + nosniff, giới hạn DOCX, `DOCS_ACCESS`, `pnpm.overrides` cho postcss.
- Vận hành: `/v1/health` báo commit đang chạy; E2E cloud cô lập (lớp `E2E`, bài `[E2E]` bị rút sau mỗi lần chạy); backup/reset có script.
- `/login` không còn kẹt "Đang tải…" (timeout + trạng thái lỗi có nút Thử lại).

## Changed files

- `apps/api/app/guest`, `routers/guest.py`, `seed/{passwords,accounts,survey}.py`, `alembic/versions/0002_guest.*` — khách, tài khoản và lớp demo.
- `apps/web/app/{login,thu}`, `src/lib/http.ts`, `src/features/guest.tsx`, `next.config.ts` — đăng nhập khách, timeout, header bảo mật.
- `scripts/ops/{reset_demo_db,rotate_passwords,backup_demo_db,purge_guests}.py` — vận hành DB.
- `apps/web/tests/release-1911/*` — E2E cloud (390/768/1280/WebKit) + khách + cô lập.
- `docs/operations/{DEPLOY-cloud,RUNBOOK}.md`, `docs/security/SECURITY-REVIEW-2026-11-20.md`, `docs/survey/*`, `docs/demo/*` — tài liệu.

## Interfaces

- Added: `/v1/auth/{config,guest,guest/resume}`, `/v1/admin/survey/{export.csv,stats}`, `commit` trong `/v1/health`, `UserOut.isGuest/surveyCode`.
- Env mới: `GUEST_ACCESS_ENABLED`, `GUEST_CLASS_CODE`, `GUEST_MAX_ACTIVE`, `GUEST_CREATE_PER_HOUR`, `DOCS_ACCESS`, `SEED_{TEACHER,REVIEWER,ADMIN,STUDENT}_PASSWORD`, `E2E_STUDENT_PASSWORD`, `NEXT_PUBLIC_SURVEY_URL`.
- Compatibility: chỉ thêm field/endpoint; tên field đóng băng không đổi.

## Verification evidence

```text
pytest 207 pass; ruff, mypy --strict sạch; web lint/typecheck/vitest 44 pass; next build OK
E2E cloud: khách 12/12 (4 viewport); luồng GV->HS đạt 390/768/1280/WebKit sau sửa test; lớp E2E cô lập kiểm local 32/32
Production (2026-11-20): /v1/health 200 + commit; HEAD 200; guestEnabled=true; khách mới thấy 1 bài seed; CSP/HSTS có; /docs 401 khi chưa đăng nhập
```

## Security/privacy impact

Chỉ mã khảo sát KS, không tên/email/IP trong DB; dữ liệu ở Neon Singapore; thời hạn lưu cần nhóm nghiên cứu chốt (đề xuất hết đợt + 90 ngày). Chi tiết: `docs/security/SECURITY-REVIEW-2026-11-20.md`.

## Risks and next action

- Render Free: ngủ sau 15 phút (UptimeRobot 5 phút giữ thức), 750 giờ/tháng, không SLA. Bộ đếm giới hạn nằm trong bộ nhớ.
- Auto-Deploy Render phải bật (đã gặp mã mới không chạy sau merge). Kiểm bằng `/v1/health`.
- Tồn đọng: CSP còn `'unsafe-inline'` cho script; GV dùng chung một mật khẩu seed; không MFA admin; chưa làm lại UI (các pha UI chờ duyệt).
- Việc sau đợt khảo sát: xuất CSV, chốt thời hạn lưu, subdomain trường, máy chủ trong nước cho dữ liệu thật.

## Update 2026-11-20 (sau reset cloud)

- Reset DB demo xong: 6 bài seed, KS có 1 assignment thêm, lớp E2E + `E2E-1`. Health ok, `guestEnabled=true`, khách mới chỉ thấy bài seed.
- Mật khẩu Neon đã đổi (lộ trong chat) và `DATABASE_URL` Render đã cập nhật; mật khẩu admin đã rotate, `SEED_ADMIN_PASSWORD` Render đã đồng bộ.
- E2E cloud 44 pass, 1 fail (T1 @390, `Refused to apply style … text/plain`). Chẩn đoán: hash `0b79d5a8…` trả 404 text/plain trên Vercel, HTML hiện tại của mọi route trỏ `4fe710ae…` (200 text/css, immutable), không có middleware hay `headers()` ghi đè `/_next/static` -> lệch bản deploy khi chạy E2E đúng lúc deploy sau merge. Thêm `tests/release-1911/static-assets.spec.ts` (chỉ GET). Không chạy lại E2E ghi dữ liệu lên cloud trừ khi được yêu cầu.
- `pg_dump` 16 không dump được Neon PG18: `backup_demo_db.py` chạy `postgres:18` qua Docker. Production PG18, CI/compose PG16: nâng trong PR riêng (chưa làm).
