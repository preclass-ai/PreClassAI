# Task: T13 — Connect FE to backend v2 and meet the v1.0 handoff UI rules

Status: `in_review`
Owner: Thiện (Claude Code) · review: Thiện
Created: 2026-11-14

## Goal

`apps/web` runs end to end against Khải's merged backend (`main`, PR #4) and meets the UI rules in `docs/v2/PreClass_AI_Source_to_Output_Traceability_v1.0_Dev_Handoff.docx` §4 and §10, within what API `0.1.0-v0` supports.

## Scope

- In scope:
  - S03 layout: about 63/37 on desktop, inspector as a bottom sheet on mobile. Approve, request changes and reject sit next to the selected block.
  - Warnings use text plus an icon, never colour alone.
  - Autosave of unsaved block edits.
  - S06 read-only view of any revision.
  - E2E against the seeded stack.
- Out of scope: changing the API or schema. Requirements the API does not support are listed under Backend gaps.

## Superseded or skipped (plan updated)

- `docs/v2/PreClass_Backend_Plan_v2.md`, FE column for 13–16/11 ("S01 bằng mock", "S02/S03 dùng Prism mock"): skipped. The real API is merged and every screen calls it.
- `apps/console` (contract-preview app with MOCK fallback): reference only. `apps/web` replaces it for FE work. Removing it is Khải's call because its CI job is his.
- T12 plan, Task 3 step 1 (failing test for presentation-only edits): skipped. The new behaviour is tested here instead.

## Backend gaps for Khải (do not fake in the FE)

- S02 asks for 1 of 4 P0 formats (slides, worksheet, flashcards, visual story). `GenerateRequest.outputType` only accepts `WORKSHEET | FLASHCARDS`.
- Flashcard flip and student flashcard interaction: no API flow, so students see only the front.
- AT-01 diff highlight: VAL-02 `evidence` is free-form JSON, so the FE shows it raw. A stable `{expected, actual}` shape would allow a real diff view.

## Verification

- [x] `corepack pnpm@10 --filter @preclass/web lint`, `typecheck`, `test` (31), `build`: all exit 0
- [x] `corepack pnpm@10 --filter @preclass/web test:e2e` against API :8000 + dev :3000 (seeded): 16 pass, 2 skipped on purpose
- [x] Mobile bottom sheet screenshot at 390 px, light and dark

## Handoff

`.agents/handoffs/T13-fe-v1-requirements.md`
