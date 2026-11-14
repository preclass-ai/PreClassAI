# Deployment runbook

## Environments

- `local`: mock seed, local PostgreSQL, no real credentials.
- `staging`: mock-only data, separate database and low-limit LLM key.
- `production`: consented data only, separate secrets and database, manual approval.

Copy `infra/.env.staging.example` or `infra/.env.prod.example` to the corresponding untracked `.env.staging` or `.env.prod` file on the host; never commit those files.

## Release flow

1. Merge a reviewed PR with green CI.
2. Build and push an immutable image tagged with commit SHA.
3. Deploy staging and run health, smoke, and responsive checks.
4. Confirm backup freshness and migration rollback path.
5. Obtain production approval from the Tech Lead; notify the mentor/school owner.
6. Run database migration, deploy, and verify `/api/health` and `/api/ready`.
7. Monitor errors, latency, disk, memory, tunnel, and AI quota for 30 minutes.

## Rollback

Prefer application image rollback. If a migration is not backward-compatible, stop and restore using the documented database procedure; never improvise destructive SQL on production.

## Pilot host checklist

- SSH key-only access, UFW, fail2ban, automatic security updates.
- Docker restart policy and documented power/network recovery.
- Cloudflare Tunnel credentials stored outside the repository.
- Host owner and on-call person documented before enabling real data.

## API workers (bắt buộc `--workers 1`)

Rate limit đăng nhập (`app/auth`) giữ bộ đếm trong bộ nhớ tiến trình (quyết định P0, review Khải 14/11). Chạy `uvicorn app.main:app --workers 1`; nhiều worker làm giới hạn lỏng đi theo số worker. Nếu cần scale ngang, chuyển bộ đếm sang DB/Redis trước.
