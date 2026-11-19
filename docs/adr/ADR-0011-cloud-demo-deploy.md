# ADR-0011 — Triển khai demo trên cloud miễn phí (Vercel + Render + Neon)

Status: `proposed` · Date: 2026-11-19 · Deciders: Khải · Liên quan: ADR-0010

## Context

Cần một URL công khai ổn định cho buổi nghiệm thu/thi, không tốn phí, không phụ thuộc laptop. Laptop preview (tunnel) giữ làm dự phòng.

## Decision

- **Web** `apps/web` trên Vercel (`https://preclass-ai.vercel.app`); **API** `apps/api` trên Render Free (Singapore); **DB** Neon Free Postgres 16 (Singapore). Chỉ seed "DỮ LIỆU MINH HỌA", `LLM_PROVIDER=mock`, `APP_ENV=demo`.
- **Một origin:** Next rewrite `/v1/*`, `/docs`, `/openapi.json` sang `API_ORIGIN` (biến build trên Vercel). Trình duyệt không gọi `onrender.com`; cookie giữ `Secure`, `HttpOnly`, `SameSite=Lax`; CSRF chấp nhận `FRONTEND_ORIGIN`.
- API chạy `uvicorn --proxy-headers --forwarded-allow-ips='*'` với 1 worker, nên giới hạn đăng nhập dùng IP thật từ `X-Forwarded-For` (Vercel đặt giá trị này), không gộp mọi người vào IP của Vercel/Render.
- DB dùng chuỗi **direct** của Neon (migration và asyncpg không qua PgBouncer); pool 5, không overflow, `pool_pre_ping`, `pool_recycle=300`.

## Trade-offs

- Render Free **ngủ sau 15 phút** không có request; cold start ~30–60 s, request đầu qua Vercel có thể 504. Giảm bằng UptimeRobot (5 phút) và mở link trước buổi demo 1 phút.
- Giới hạn free: 512 MB RAM, 0,1 CPU, Neon tự suspend compute khi rảnh (thức lại ~1 s), dung lượng nhỏ, không SLA, không backup có cam kết.
- Rate limit đăng nhập nằm trong bộ nhớ một tiến trình: restart/ngủ là reset.
- Seed dùng mật khẩu demo đã biết: cloud demo không được chứa dữ liệu thật.

## Consequences

Bản cloud chỉ chứa dữ liệu minh họa; triển khai với dữ liệu học sinh thật sẽ chạy trên máy chủ trong nước.
Hướng dẫn vận hành: `docs/operations/DEPLOY-cloud.md`.
