# Backend GĐ10 + Web FE (Thiện) — preview cho test 18/11

Mở PR: https://github.com/preclass-ai/PreClassAI/compare/main...feat/backend-v2?expand=1

## Thay đổi chính
- Backend GĐ10: Docker staging/prod, `scripts/smoke.py`, backup/restore, RUNBOOK, `OpenAICompatibleProvider`, nguồn text dạng bảng → anchor `TABLE_CELL`.
- Toàn bộ `apps/web` (Next.js, S01–S07) + `packages/api-client` do Thiện làm (nhánh `feat/web-frontend`, đã gộp vào nhánh này). **Phần `apps/web` cần Thiện review.**
- Preview máy cá nhân: `scripts/ops/preview*.ps1` (Postgres → API → Prism → Next → Caddy → tunnel), task đăng nhập + health check; `Caddyfile.preview` route `/` tới Next.
- Thêm test AT-07 dạng skip (P1 ảnh); AGENTS.md: quy ước nhánh `feat/web-*` / `feat/api-*`.
- 21 commit so với `main`; không xung đột (`git merge-tree` sạch).

## Kết quả kiểm tra thật (máy dev, 17/11)
- `ruff check`: sạch · `mypy --strict app`: 0 lỗi / 31 file
- `pytest` (có Postgres): **162 passed, 1 skipped (AT-07)**, 134 s
- OpenAPI khớp code; Spectral 0 lỗi (1 cảnh báo `servers`); `schema.d.ts` khớp; api-client + console typecheck/build OK
- Web: `pnpm install --frozen-lockfile`, lint, typecheck OK; vitest 31/31 pass
- `next build`: biên dịch OK, trên Windows thoát lỗi EPERM ở bước symlink `standalone` (giới hạn quyền máy; Docker/Linux build OK ngày 16/11)
- Chưa chạy được ở máy: job CI `stack` (cần build Docker), Playwright E2E, job `app` trên runner thật

## Preview
- URL (đổi khi tunnel khởi động lại): https://cleared-ambien-industry-taste.trycloudflare.com — có basic auth, mật khẩu gửi riêng.
- Tài khoản seed (dữ liệu minh họa), mật khẩu `preclass-demo`: GV `gv.dia@preclass.local`; duyệt `reviewer@preclass.local`; quản trị `admin@preclass.local`; học sinh `HS10-01..15`, `HS11-01..15`.
- Smoke qua tunnel: health, /docs, trang FE; GV đăng nhập → bài "Phân bố dân cư theo vùng" → 15 block + provenance; HS nộp 1 câu MCQ → có giải thích.

## Khác biệt hợp đồng / khoảng trống đã biết
- Client sinh từ `openapi.json` khớp từng byte; FE dùng API thật, không dùng Prism.
- Chưa làm ở FE: 4 định dạng S02, lật thẻ, diff VAL-02 (T13).
- VAL-07 là stub, VAL-08 chỉ list mẫu. Docstring `app/main.py` còn ghi "501" (lỗi thời).
- `--workers 1` (rate limit đăng nhập nằm trong bộ nhớ) chưa ghi vào RUNBOOK.

## Checklist test cho Thiện (S01–S07)
- [ ] S01 Source Library: nhập text/DOCX, xem anchor
- [ ] S02 Generate: sinh bản nháp (mock), lỗi hiển thị tiếng Việt
- [ ] S03 Editor + Source Inspector: sửa block, autosave, 409 `VERSION_CONFLICT`
- [ ] S04 Review Queue: duyệt/từ chối, `STALE_REVIEW`
- [ ] S05 Publish Gate: chặn khi còn lỗi VAL, xuất bản, giao lớp
- [ ] S06 History
- [ ] S07 Student View: làm trước, thấy giải thích sau; 390/768/1280 px

Không merge trước khi Thiện review `apps/web` và CI xanh.
