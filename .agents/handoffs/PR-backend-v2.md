# Draft PR: Backend v2 – API contract v0

Dán nội dung này làm mô tả PR (Draft) từ `feat/backend-v2` → `main`. Không merge trước khi Khải review.

## Cho Thiện (frontend)
- Hợp đồng: [`apps/api/openapi/openapi.json`](../../apps/api/openapi/openapi.json) · [`docs/api/API_GUIDE.md`](../../docs/api/API_GUIDE.md) · [`docs/api/DATA_MODEL.md`](../../docs/api/DATA_MODEL.md)
- Mock theo ví dụ: `npx @stoplight/prism-cli mock -p 4010 apps/api/openapi/openapi.json`
- Client có kiểu: `packages/api-client` (`npm ci && npm run gen:api`; README có ví dụ xử lý lỗi RFC 9457 theo `code`).
- Dev console tham khảo (không phải UI sản phẩm): `apps/console` (`npm run dev`, tự dùng mock cho route chưa làm, gắn nhãn MOCK).
- Docs tương tác: `/docs` (Scalar) khi chạy API.
- Preview chạy thật qua tunnel (URL đổi mỗi lần khởi động lại, basic auth): Khải gửi riêng.
- Tài khoản seed (mật khẩu `preclass-demo`, chỉ dev): `gv.dia@preclass.local`, `gv.khac@preclass.local`, `reviewer@preclass.local`, `admin@preclass.local`, `HS10-01…15` (10A1), `HS11-01…15` (11A1). Dữ liệu: **DỮ LIỆU MINH HỌA**.

## Đã chạy thật
`POST /auth/login`, `POST /auth/logout`, `GET /me`, `GET /classes`, `GET /admin/audit-logs`, `PUT /revisions/{id}/sources`. Còn lại 501 cho tới GĐ5–9.

## Khác đặc tả (đã chốt, Khải duyệt 14/11)
1. Cookie session, không có `/auth/refresh`; header `X-PreClass-CSRF: 1` trên mọi request không phải GET.
2. Upload DOCX tách `POST /sources/docx`, `POST /sources/{id}/revisions/docx`.
3. Thêm `PUT /revisions/{id}/sources`, `GET /classes/{id}/assignments`, `GET /admin/audit-logs`.
4. Block trả phẳng (`parentId` + `position`); payload camelCase.
5. Source revision mới không tự đổi bài; `PUT /revisions/{id}/sources` đánh REVIEW_AGAIN block liên quan trong một transaction (AT-08).
6. Khóa revision khi PUBLISHED/SUPERSEDED (không phải "khác DRAFT"); duyệt gắn `content_hash`.
7. Chưa có cursor pagination (envelope `{items,nextCursor}` có sẵn).

## Kiểm chứng
`pytest` 64 test (gồm marker `db`, Postgres 16), `ruff`, `mypy --strict` xanh. CI: lệch `openapi.json`, Spectral, client sinh lại, build console.
