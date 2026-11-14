# T9 progress

- 2026-11-14 GĐ0: D-001 accepted; prompt v2 cập nhật theo C-01..C-24.
- 2026-11-14 GĐ1: khung `apps/api` (config, RFC 9457, `/v1/health`), compose dev/staging/prod + Caddy cùng origin, CI job Python, ADR-0010, banner Superseded.
- 2026-11-14 GĐ2: models + migration `0001` (DDL đóng băng + trigger + 2 role DB), seed 6 bài mock + 34 user, `DATA_MODEL.md`; test trigger/migration up-down-up/invariant (`@pytest.mark.db`) xanh trên Postgres local.
- 2026-11-14 GĐ3: **Hợp đồng API v0 sẵn sàng cho frontend.** 39 operation, schema + ví dụ, `apps/api/openapi/openapi.json`, `docs/api/API_GUIDE.md`; Prism mock chạy đúng; test snapshot OpenAPI + ví dụ validate. Freeze v1 sáng 16/11. Chờ review Khải.
- 2026-11-14 GĐ4 (một phần): auth thật — cookie session (chỉ lưu sha256 token), argon2, CSRF header + Origin, rate limit đăng nhập (trong tiến trình), `require_role` → 403 `FORBIDDEN_ROLE`, audit LOGIN/LOGOUT; chạy thật `login/logout/me/classes/audit-logs`; 18 test auth xanh. **Chưa có:** test IDOR cho source/lesson/block (route chưa tồn tại, làm cùng GĐ5/6) và STUDENT chặn mọi route GV (kiểm khi từng route được viết).
- 2026-11-14 Review Khải GĐ1–4: **GĐ4 đạt một phần.** Test IDOR (10.1) cho source/lesson/block/student là điều kiện **bắt buộc** của cổng GĐ5, GĐ6 và GĐ9. Mỗi cổng chạy FULL `pytest` (gồm marker db) + `ruff` + `mypy --strict` rồi mới báo xanh. Đã làm: PUT sources (AT-08) một transaction + test, test nhanh (<30 s), seed chặn production.
- 2026-11-14 Contract preview: `packages/api-client` (types + CI), `apps/console` (5 màn, MOCK fallback), `/docs` Scalar, `scripts/ops/preview*.ps1` + `infra/Caddyfile.preview`, CI Spectral + OpenAPI drift. Chạy staging tạm qua cloudflared quick tunnel.
