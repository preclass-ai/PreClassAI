# Handoff: T11 — Frontend v2 (`apps/web`)

Status: `in_review`
Owner/harness: Thiện · Claude Code
Date: 2026-11-14

## Outcome

`apps/web` là app Next.js 15 (App Router, TypeScript strict, React Query) gọi API `/v1` thật qua `@preclass/api-client`.
Có đủ Login, S01 Source Library, S02 Generate, S03 Editor + Source Inspector, S04 Review Queue, S05 Publish Gate + giao bài +
thu hồi, S06 History, S07 Student (mobile), lớp/tiến độ, audit log. Khung cũ (H.A.B.I.T, route handler, `src/db`…) đã bỏ.

## Changed files

- `apps/web/**` — app mới (routes `app/`, logic `src/`, test `tests/`, `Dockerfile`, `playwright.config.ts`)
- `pnpm-workspace.yaml`, `package.json`, `pnpm-lock.yaml` (root) — pnpm workspace `apps/web` + `packages/api-client` (job CI `app` chạy ở root)
- `.dockerignore`, `.gitignore` (`*.tsbuildinfo`)
- `AGENTS.md` (lệnh frontend), `CLAUDE.md` (kiến trúc FE, sửa lệnh alembic), `apps/web/README.md`

## Interfaces

- Added/changed: không đổi API. Dev: Next `rewrites` `/v1/*` → `API_ORIGIN` (mặc định `http://localhost:8000`). Prod: image `preclass-web` (standalone, :3000) sau Caddy.
- Compatibility notes: `packages/api-client` giữ `package-lock.json` cho job CI `api-client`/`console` (npm); pnpm dùng nó qua `workspace:*`.

## Verification evidence

```text
pnpm typecheck / lint            → sạch
pnpm test (vitest)               → 4 file, 23 test pass
pnpm build (next 15.5)           → 11 route, build OK
playwright (390/768/1280)        → 16 passed, 2 skipped (luồng ghi chỉ chạy ở 1280), chạy 2 lần liên tiếp đều xanh
docker build + run               → GET /login 200
```

## Audit 14/11 (đã sửa)

- Open redirect sau đăng nhập (`?next=/\evil.com`) → `src/lib/redirect.ts` + test.
- Root `package.json` bỏ `packageManager` (xung đột với `version: 10` của `pnpm/action-setup@v4` trong CI).
- Thêm `app/error.tsx`, `app/not-found.tsx`.

## Security/privacy impact

Không lưu token: phiên là cookie HttpOnly; mọi request không phải GET gửi `X-PreClass-CSRF: 1`. `next` sau đăng nhập chỉ nhận
đường dẫn nội bộ. Guard vai trò ở FE chỉ để UX; server vẫn quyết định. HS không gọi provenance/đáp án. Không có dữ liệu thật.

## Risks and next action

- Risks: E2E làm thay đổi seed (mỗi lần chạy thêm một revision cho `dan-so-vung`, HS10-03..05 đã trả lời) — chỉ chạy trên dev/staging.
  Thẻ ghi nhớ chỉ hiển thị mặt trước (API chưa có luồng lật thẻ). Chưa có chế độ tối kiểm tra kỹ bằng mắt.
- Next action: Thiện review (người review phần frontend); bật biến repo `APP_CI_ENABLED=true` để CI chạy job `app`; build/push image `preclass-web` cho staging (H2 17/11).

## Codex review follow-up (14/11)

- Re-ran `corepack pnpm@10 --filter @preclass/web lint`, `typecheck`, `test`, and `build`: all passed (23 Vitest tests, 11 built routes). `git diff --check` and `git diff --cached --check` passed.
- UI review initially found a missing skip link and login input `name` attributes; the addendum below records their fixes.
- `gh auth status` reported an invalid token, but authenticated `gh api` requests succeeded. On 14/11, created the repository variable `APP_CI_ENABLED=true` and confirmed its value with `gh api`. The app job can run on the next qualifying CI event.

## Codex review addendum — 2026-11-14

- Found and fixed a logout failure path: a network/server error no longer clears the local user and presents login while the server session might remain active. The shell now shows an error and leaves the user signed in so they can retry. A 401 still clears local state because the session has already expired.
- Resolved the earlier UI findings: the shell has a focusable skip link to main content, and both login controls have `name` attributes.
- Changed: `apps/web/src/lib/auth.tsx`, `apps/web/src/components/shell.tsx`, `apps/web/app/globals.css`, `apps/web/app/login/page.tsx`, `apps/web/tests/auth-ui.test.tsx`.
- Regression tests failed against the old behavior, then passed after the fixes. Fresh sequential verification with `corepack pnpm@10 --filter @preclass/web`: lint, typecheck, test (26 passed), and build (11 routes) all exited 0. The first typecheck overlapped with `next build` and saw transient missing `.next/types` files; the sequential rerun passed.
- The local web server was not running (`localhost:3000` connection refused), so this review did not rerun Playwright or Docker. T11 remains `in_review`; the app CI repository variable is now enabled, and the next qualifying CI event will exercise the job.
