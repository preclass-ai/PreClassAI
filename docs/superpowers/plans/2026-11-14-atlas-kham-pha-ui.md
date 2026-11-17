# Atlas khám phá UI Implementation Plan

> Execute task by task; steps use checkbox (`- [ ]`) syntax. Use only skills shipped in `.agents/skills/` (harness-specific plugins are not available to every harness). Status 2026-11-14: **done**, see `.agents/handoffs/T12-atlas-ui-refresh.md`.

**Goal:** Refresh every PreClass AI web screen into a friendly, modern Geography experience for high-school students and teachers without changing API behavior.

**Architecture:** Keep existing Next.js routes and React Query data flows. Introduce a coherent CSS token and component layer, then apply page-specific layouts and copy. Use lightweight CSS/SVG geography motifs and progressive enhancement for motion.

**Tech Stack:** Next.js 15, React 19, TypeScript, CSS, Vitest, Playwright.

**Spec:** `docs/superpowers/specs/2026-11-14-atlas-kham-pha-ui-design.md`

## Global Constraints

- Subject is **Địa lí**. No API/schema, authorization, grading, or data changes.
- Never reveal student explanations before submission. Preserve the illustrative-data notice.
- No heavy imagery or animation dependency. Motion 120–220 ms and reduced-motion support.
- Mobile target 390 px; verify 768 and 1280 px and dark mode.
- ~~Current `apps/web` is untracked user work; do not commit.~~ Superseded 2026-11-14: Thiện takes the work to a PR on `feat/web-frontend` (T13).

## Review Focus

- A long Vietnamese title wraps without clipping in cards and headers: inspect 390 px screenshot in Tasks 2–4.
- Empty, loading, and error states remain legible: inspect each state in Tasks 2–4.
- A teacher's dense editor and publish checklist remain usable at 390 px: inspect in Task 3.
- Student choices and explanations remain separated by submission: run existing student E2E in Task 4.
- Keyboard focus and reduced motion remain usable: inspect CSS and browser behavior in Task 4.

---

### Task 1: Shared Atlas system

**Files:** `apps/web/app/globals.css`, `apps/web/src/components/shell.tsx`, `apps/web/src/components/ui.tsx`, `apps/web/app/layout.tsx`, `apps/web/tests/auth-ui.test.tsx`.

**Interfaces:** Existing `AppShell`, `Button`, `Badge`, `PageHeader`, `Notice`, `ErrorBox` props stay unchanged. New CSS classes may be added for hero and icon accents.

- [x] Existing semantic shell test retained; presentation-only CSS handled by visual review (ruling in ledger).
- [x] Replace grey/blue tokens with Atlas palette, typography, depth, focus, hover, dark tokens, and reduced-motion rule; refresh shell and shared controls without changing their contracts.
- [x] Run focused tests, lint, and typecheck; viewport review carried into Task 4.

### Task 2: Login and student journey

**Files:** `apps/web/app/login/page.tsx`, `apps/web/app/(student)/student/page.tsx`, `apps/web/app/(student)/student/assignments/[assignmentId]/page.tsx`, `apps/web/app/globals.css`, `apps/web/tests/auth-ui.test.tsx`.

**Interfaces:** Keep the login POST, student list/detail GETs, attempt POST, and result gating unchanged. New presentation-only classes and derived counts are local to these pages.

- [x] Render test for real assignment counts + illustrative-data notice (`tests/student-home.test.tsx`).
- [x] Build atlas login hero, student overview and assignment cards; improve question/option/result visual hierarchy and tap sizes. Keep answer submission behavior unchanged.
- [x] Run focused tests and inspect 390/768/1280 px (E2E screenshots); student E2E updated for the new heading.

### Task 3: Teacher and admin journey

**Files:** `apps/web/app/(teacher)/**/page.tsx`, `apps/web/src/features/*.tsx`, `apps/web/app/(admin)/admin/audit/page.tsx`, `apps/web/app/globals.css`.

**Interfaces:** All API calls and status codes stay unchanged. Existing editor/review/publish workflows remain intact.

- [~] Skipped: teacher styling is presentation-only; new behaviour (review actions in S03, autosave, snapshot view) is tested under T13.
- [x] Apply Atlas section headers, cards, action hierarchy, editor/inspector surfaces, review/publish states, class progress and audit table styling. Avoid bulk approve or new grading indicators.
- [x] Run lint/typecheck/test; inspect dense editor and publish gate at 390/768/1280 px.

### Task 4: Full verification and handoff

**Files:** `.agents/tasks/T12-atlas-ui-refresh.md`, `.agents/handoffs/T12-atlas-ui-refresh.md`, `docs/ui/README.md`.

**Interfaces:** Document visual tokens and responsive behavior; no API changes.

- [x] Run sequential `corepack pnpm@10 --filter @preclass/web lint`, `typecheck`, `test`, `build` and record exit codes.
- [x] Run seeded-stack Playwright if available; otherwise record exact local blocker. Inspect screenshots at 390/768/1280 px, dark mode, reduced motion, keyboard focus.
- [x] Run `git diff --check`, inspect changed files, update task/handoff with results and remaining risks.

## Self-review

All spec sections map to Tasks 1–4. Shared components keep existing signatures; page-specific UI consumes those styles. The review focus covers content length, states, mobile density, answer gating, and accessibility. No backend or data decision is required.
