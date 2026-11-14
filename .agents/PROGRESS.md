# T9 progress

- 2026-11-14 GĐ0: D-001 accepted; prompt v2 cập nhật theo C-01..C-24.
- 2026-11-14 GĐ1: khung `apps/api` (config, RFC 9457, `/v1/health`), compose dev/staging/prod + Caddy cùng origin, CI job Python, ADR-0010, banner Superseded.
- 2026-11-14 GĐ2: models + migration `0001` (DDL đóng băng + trigger + 2 role DB), seed 6 bài mock + 34 user, `DATA_MODEL.md`; test trigger/migration up-down-up/invariant (`@pytest.mark.db`) xanh trên Postgres local.
- 2026-11-14 GĐ3: **Hợp đồng API v0 sẵn sàng cho frontend.** 39 operation, schema + ví dụ, `apps/api/openapi/openapi.json`, `docs/api/API_GUIDE.md`; Prism mock chạy đúng; test snapshot OpenAPI + ví dụ validate. Freeze v1 sáng 16/11. Chờ review Khải.
