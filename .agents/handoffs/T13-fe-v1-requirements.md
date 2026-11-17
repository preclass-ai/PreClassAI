# Handoff: T13 — FE connected to backend v2 + v1.0 handoff UI rules

Status: `in_review`
Owner/harness: Thiện · Claude Code
Date: 2026-11-14

## Outcome

The frontend runs end to end against Khải's backend (`main`, contract `0.1.0-v0`, 39 operations) with no mocks. The handoff's S03, S06 and §10 UI rules are implemented where the API supports them.

## Changed files

- `apps/web/src/features/review.tsx`: shared `ReviewActions` (hash-bound; no approve-all), used by S04 and S03
- `apps/web/src/features/editor.tsx`:
  - review actions beside the selected block
  - autosaved edits
  - focus moves to the panel heading; Esc closes the panel
  - `.open` class for the mobile sheet
- `apps/web/src/lib/draft.ts` (new): `useDraft`, session-storage autosave keyed by block and version
- `apps/web/src/features/history.tsx`: S06 "Xem bản #n", a read-only block tree of any revision
- `apps/web/app/login/page.tsx`: `method="post"` (see Security)
- `apps/web/app/globals.css`:
  - 63/37 split and the mobile bottom sheet
  - icons on badges and alerts
  - Atlas teacher surfaces, `.sr-only`
- Tests:
  - `tests/draft.test.tsx` (new, 3 tests)
  - `tests/auth-ui.test.tsx` (+1 test)
  - E2E `teacher.spec.ts`: review actions in the inspector; closes the sheet
  - E2E `publish-flow.spec.ts`: snapshot view
  - E2E `student.spec.ts`: new heading
- `docs/tooling/skills.md` (two new skills), `.github/workflows/ci.yml` (outdated comment), `docs/ui/README.md`, `CLAUDE.md`

## Interfaces

- No API change. Uses `GET /v1/revisions/{id}/blocks` for older revisions (it allows reads in any state).

## Verification evidence

```text
corepack pnpm@10 --filter @preclass/web lint|typecheck|test|build  → exit 0 each; Vitest 7 files / 31 tests
pnpm test:e2e (API :8000 seeded, dev :3000)                         → 16 passed, 2 skipped (write flow desktop-only)
git diff --check                                                    → clean
```

Note: running `next build` while `next dev` is running overwrites `.next`, and the dev server then serves pages without JS (all E2E fail at login). Stop dev or `rm -rf apps/web/.next` before restarting.

## Security/privacy impact

- Fixed: the login form had no `method`. Submitted before hydration, it sent `GET /login?identifier=…&password=…`, which put the password in the URL, the dev-server log and browser history. It is now `method="post"`, with a regression test.
- Autosaved drafts stay in `sessionStorage` (this tab only), never in the URL or on the server. No student data is involved: only teachers edit blocks.

## Risks and next action

- Risks:
  - E2E changes the seed (adds a revision of `dan-so-vung` on each run).
  - `APP_CI_ENABLED=true` makes the `app` job fail on PRs into `main` until this branch merges, because `main` has no root pnpm workspace.
- Next actions:
  1. Thiện reviews and opens the PR from `feat/web-frontend`.
  2. Khải triages the backend gaps listed in `.agents/tasks/T13-fe-v1-requirements.md`.
