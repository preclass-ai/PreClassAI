# Task: T11 — Frontend v2 (`apps/web`, Next.js) theo Source-to-Output Traceability

Status: `done`
Owner: Thiện (thực hiện bằng Claude Code) · review: Thiện
Created: 2026-11-14

## Goal

`apps/web` chạy được các màn Login, S01–S07, lớp/tiến độ, audit trên API `/v1` thật (thay khung Next.js full-stack cũ).

## Scope

- In scope: mọi màn ở `docs/api/API_GUIDE.md` §3; responsive 390/768/1280; xử lý lỗi theo `code`; Dockerfile image `preclass-web`.
- Out of scope: sửa `apps/api` / hợp đồng OpenAPI; deploy staging/production; bật biến CI `APP_CI_ENABLED`.

## Interfaces and decisions

- Inputs: `apps/api/openapi/openapi.json` qua `packages/api-client`.
- Outputs: `apps/web/`, root `pnpm-workspace.yaml` + `package.json` + `pnpm-lock.yaml`, `apps/web/Dockerfile`, `.dockerignore`.
- ADRs / docs: ADR-0010, D-001, `docs/api/API_GUIDE.md`.

## Verification

- [x] `pnpm lint && pnpm typecheck && pnpm test && pnpm build` (repo root)
- [x] `pnpm --filter @preclass/web test:e2e` trên stack local đã seed (16 pass, 2 skip có chủ đích)
- [x] `docker build -f apps/web/Dockerfile .` + container trả `/login` 200

## Handoff

`.agents/handoffs/T11-web-frontend.md`

2026-11-14 (Thiện): closed. Re-verified against the live backend under T13 (E2E 16 pass, 2 intentional skips). Remaining review happens on the `feat/web-frontend` PR. Staging image push moves to the H2 deploy (owner Khải).
