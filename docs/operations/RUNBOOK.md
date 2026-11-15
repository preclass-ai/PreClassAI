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
| Chạy `up` lỗi cổng 80/443 | cổng bị chiếm; dừng dịch vụ đang dùng |

## Rollback

`IMAGE_TAG=<tag cũ> docker compose -f compose.prod.yml up -d`. Migration chỉ tiến (`alembic upgrade head` lúc khởi động); lùi schema cần `alembic downgrade` thủ công **sau khi backup**.
