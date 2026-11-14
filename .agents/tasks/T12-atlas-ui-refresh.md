# Task: T12 — Atlas khám phá UI refresh

Status: `done`
Owner: Codex (Tasks 1–2), Claude Code (Tasks 3–4) · review: Thiện
Created: 2026-11-14

## Goal

Toàn bộ `apps/web` có giao diện Địa lí thân thiện với học sinh THPT, sinh động và hiện đại, giữ nguyên luồng API và quy tắc nội dung.

## Scope

- In scope: design tokens, shell, đăng nhập, màn học sinh, giáo viên và admin; responsive, dark mode, motion và accessibility.
- Out of scope: đổi API/schema, quyền, logic chấm điểm, dữ liệu thật, deploy.

## Interfaces and decisions

- Inputs: `apps/web`, `docs/api/API_GUIDE.md`, T11 handoff.
- Outputs: CSS/components/pages trong `apps/web`, ảnh kiểm tra và handoff T12.
- ADRs / docs: `docs/superpowers/specs/2026-11-14-atlas-kham-pha-ui-design.md`; ADR-0010 vẫn giữ ranh giới FE/API.

## Verification

- [x] `corepack pnpm@10 --filter @preclass/web lint`
- [x] `corepack pnpm@10 --filter @preclass/web typecheck`
- [x] `corepack pnpm@10 --filter @preclass/web test`
- [x] `corepack pnpm@10 --filter @preclass/web build`
- [x] Kiểm tra giao diện 390/768/1280 px, dark mode, focus và reduced motion; Playwright với seeded stack nếu có.

## Handoff

`.agents/handoffs/T12-atlas-ui-refresh.md`. Design approved by Thiện on 2026-11-14 (he asked to finish the implementation).
