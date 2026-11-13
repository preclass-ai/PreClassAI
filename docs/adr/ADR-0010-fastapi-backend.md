# ADR-0010 — Backend FastAPI cho PreClass AI v2

Status: `accepted` · Date: 2026-11-14 · Deciders: Khải · Supersedes: ADR-0001 (và một phần ADR-0002, 0005, 0006, 0008 trong `docs/01`)
Nguồn đầy đủ: `.agents/decisions/D-001-backend-v2-direction.md` (Q1–Q9, tất cả chọn phương án khuyến nghị).

## Context

Sản phẩm chuyển từ H.A.B.I.T/Ngữ văn (học sinh tự học + AI tutor) sang Source-to-Output Traceability cho Địa lí (giáo viên duyệt học liệu có truy nguồn). Repo chưa có mã ứng dụng nào nên không có chi phí chuyển đổi mã.

## Decision

- Backend là **FastAPI (Python 3.12) ở `apps/api/`**, PostgreSQL 16, SQLAlchemy 2 async, Alembic. Frontend Next.js (Thiện, `apps/web/`) gọi REST `/v1`.
- Hợp đồng là OpenAPI sinh từ Pydantic (`apps/api/openapi/openapi.json`); v0 14/11, freeze v1 16/11.
- Cùng origin qua Caddy (`/v1/*` → api); phiên bằng cookie session phía server.
- Bất biến ép ở DB (trigger, role `preclass_app` không UPDATE/DELETE bảng append-only) và service (khóa hàng khi duyệt/publish).
- Phạm vi P0: Worksheet trước, Flashcards sau; nguồn là text và DOCX. Slides, Visual Story, PPTX/PDF/OCR, block `image/callout/slide/story_scene` đã cắt khỏi đặc tả P0 (Product chưa ack).
- ADR cũ, `docs/01`, `02`, `05`, `06`, `drizzle/` được đánh dấu Superseded, không viết lại.

## Consequences

- (+) Một hợp đồng OpenAPI cho Thiện; DOCX, Unicode, Decimal thuận Python; PR-02/PR-05 được DB bảo vệ.
- (−) Hai toolchain (uv + pnpm), hai image; CORS/cookie giải quyết bằng cùng origin.
- Rollback: nếu Khải không review được Python hoặc hợp đồng không dùng được, quay về Next.js + Drizzle; thiết kế, hash, trigger SQL và test AT tái dùng.

Revisit: sau cổng GĐ3 và sau 18/11.
