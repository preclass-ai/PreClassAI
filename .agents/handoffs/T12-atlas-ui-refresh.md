# Handoff: T12 — Atlas khám phá UI refresh

Status: `done`
Owner/harness: Codex (Tasks 1–2) · Claude Code (Tasks 3–4)
Date: 2026-11-14

## Outcome

All of `apps/web` uses the Atlas khám phá look: design tokens (light and dark), the shell, login, the student home and assignment pages, and the teacher and admin surfaces (editor, inspector, review, publish checklist, history timeline). API calls, permissions, grading and when explanations appear are unchanged.

## Changed files

- `apps/web/app/globals.css`: tokens, Atlas components, teacher-surface pass, reduced motion
- `apps/web/src/components/{shell,ui}.tsx`, `apps/web/app/login/page.tsx`, `apps/web/app/(student)/**`: Codex, Tasks 1–2
- `apps/web/tests/student-home.test.tsx` (Codex); `apps/web/tests/e2e/student.spec.ts`: heading changed to "Bài được giao"
- `docs/superpowers/plans/2026-11-14-atlas-kham-pha-ui.md`: ticked or skipped steps, removed the reference to a harness-only skill

## Verification evidence

See the T13 handoff: the same gate covers both tasks (lint, typecheck, Vitest 31, build, Playwright 16 pass / 2 skip).
Screenshots at 390/768/1280 px are in `apps/web/test-results/screens/` (not committed). Mobile bottom sheet checked in light and dark mode.

## Security/privacy impact

None from styling.

## Risks and next action

- Font changed to Be Vietnam Pro at Thiện's request (Avenir Next rendered diacritics from a fallback font). `next/font` downloads it during `next build`, so the Docker/CI build needs network access to Google Fonts. Nothing is fetched at runtime.
- Risks: dark mode follows `prefers-color-scheme` only (no in-app toggle). Decorative glyphs use CSS `content: "…" / ""` so screen readers skip them. Older Safari versions may read them aloud.
- Next action: Thiện reviews the screenshots in the PR.
