# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Read `AGENTS.md` before acting. `AGENTS.md` is the canonical repository contract (layout, style, testing, commits, security, ADR/handoff rules); this file adds only working notes and intentionally contains no duplicate policy.

For multi-agent work:

- Read `.agents/README.md` and the relevant task/handoff record before editing.
- When a task matches a listed workflow, read `.agents/skills/<skill-name>/SKILL.md` before acting.
- Record decisions in `docs/adr/` and implementation handoffs in `.agents/handoffs/`.
- Never place student data, secrets, or private prompts in the repository or in agent context.
- Run the verification commands documented by the task before reporting completion.

## Current state

The backend is `apps/api` (FastAPI, ADR-0010); the frontend is `apps/web` (Next.js client app calling `/v1` through `@preclass/api-client`). `drizzle/` and much of `docs/01`–`docs/06` describe the superseded Next.js full-stack design; treat them as reference only. The current spec and plan are in `docs/v2/`; API usage and data model in `docs/api/`.

## Backend commands (run in `apps/api/`)

```text
docker compose -f ../../infra/compose.dev.yml up -d postgres   # creates `preclass` and `preclass_test` DBs
PYTHONPATH=. uv run python -m alembic upgrade head && uv run python -m seed.seed   # migrate + demo seed
COOKIE_SECURE=false uv run uvicorn app.main:app --reload       # API on :8000, docs at /docs
uv run pytest tests/unit/test_numbers.py::test_parse_numbers            # single test
uv run pytest -m "not db"                                       # skip tests needing Postgres
uv run python -m scripts.export_openapi                         # regenerate openapi/openapi.json
```

- Tests marked `db` are auto-skipped if Postgres isn't reachable at `TEST_DATABASE_URL` (default `...@127.0.0.1:5432/preclass_test`). The session fixture drops, re-migrates and re-seeds the test DB, and refuses DB names not ending in `_test`. Each test runs inside a rolled-back transaction (handler `commit()` only releases a SAVEPOINT).
- CI also fails if `openapi/openapi.json` differs from the code, and if `packages/api-client/src/schema.d.ts` differs from it. After any route/schema change: export OpenAPI, then `npm run gen:api` in `packages/api-client`.

## Backend architecture

Product flow ("source-to-output traceability"): teacher imports sources (text/DOCX → immutable source revisions with anchors) → AI generation job drafts content blocks for a lesson revision, each linked to source anchors (provenance) → validation rules VAL-01..09 flag problems → teacher approves block by block → publish gate produces an immutable snapshot → assignments to classes → students attempt first, then see the approved explanation.

- `app/routers/` are thin handlers; domain logic lives in package `__init__.py` modules (`app/lessons`, `app/blocks`, `app/publish`, `app/generation`, `app/validation`, `app/student`, `app/sources`, `app/auth`, `app/audit`). Pydantic DTOs are in `app/schemas.py`; ORM models in `app/db/models.py`.
- **Invariants are enforced in Postgres, not only Python.** Migrations are raw SQL (`alembic/versions/0001_schema.sql`, `0001_triggers.sql`, statements split on `-- split`). Triggers make event/audit/attempt tables append-only, source revisions/anchors and published snapshots immutable, and guard block/provenance edits and lesson-revision state transitions. A Python change that violates them fails at the DB.
- Editing a block invalidates its dependents (`app/blocks.invalidate`) and resets review status. Edits carry `version` (optimistic lock → 409 `VERSION_CONFLICT`); approvals carry `contentHash` (→ 409 `STALE_REVIEW`).
- Generation runs as an in-process async job with one worker; the provider (`app/generation/providers.py`, `LLM_PROVIDER=mock` by default) returns anchor aliases that the server maps back to real anchors. Jobs never approve anything. RUNNING jobs are marked FAILED on restart (`recover_after_restart`).
- API conventions (see `app/main.py` description): base `/v1`, camelCase JSON, session cookie + required `X-PreClass-CSRF: 1` header on non-GET, RFC 9457 problem+json errors via `ApiError` with stable `code`; another user's/class's resource returns 404, not 403. User-facing error text is Vietnamese.
- Settings come from env via `app/config.py` (`AI_ENABLED`, `REVIEWER_ENABLED`, `MOCK_INJECT` for test fault injection, etc.).

## Frontend architecture (`apps/web`)

- Every screen is a client component; the browser holds the `preclass_session` cookie, so there is no server-side data fetching. In dev `next.config.ts` rewrites `/v1/*` to the API (same origin, so the API's CSRF Origin check passes); in staging/prod Caddy routes `/v1/*` to the API before Next.
- All API calls go through `unwrap(api.GET/POST…)` in `src/lib/api.ts`, which throws `ApiError`; UI text comes from `errorMessage()` keyed on the problem `code` (`src/lib/errors.ts`). A 401 anywhere redirects to `/login?next=…`.
- Route groups `(teacher)`, `(student)`, `(admin)` each wrap pages in `RequireRole` (UX only; the server enforces roles). The lesson workspace `lessons/[lessonId]` hosts S03 editor, S04 review, S05 publish/assign, S06 history as `?tab=`; `?block=` selects a block.
- After any block/review/publish mutation call `invalidateLesson` (`src/features/lesson-data.ts`): counts, queue, gate and history all depend on it. Reviews must send the `contentHash` of the block as displayed.
- Review decisions go through `ReviewActions` (`src/features/review.tsx`), shared by S04 and the S03 inspector. Unsaved block edits autosave through `useDraft` (`src/lib/draft.ts`), keyed by block id and version.
- Don't run `next build` while `next dev` is running: both write `apps/web/.next`, and the dev server then serves pages without JS (every E2E fails at login). Stop dev or delete `.next` first.
- E2E specs change seed data (reviews, answers, a new revision of `dan-so-vung` per run); run them only against a dev/staging seed.
