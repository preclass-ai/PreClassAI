# Web app (Next.js)

Frontend for PreClass AI v2 (Source-to-Output Traceability). Calls the FastAPI backend under `/v1` with the typed
client `@preclass/api-client` (generated from `apps/api/openapi/openapi.json`). Owner: Thiện.

## Run locally

```bash
# 1. backend (see apps/api / CLAUDE.md): Postgres + migrate + seed, then
cd apps/api && COOKIE_SECURE=false uv run uvicorn app.main:app --port 8000

# 2. frontend, from the repo root
corepack pnpm@10 install
corepack pnpm@10 --filter @preclass/web dev     # http://localhost:3000
```

`COOKIE_SECURE=false` is needed over plain http. `/v1/*` is proxied to `API_ORIGIN` (default `http://localhost:8000`)
so the browser sees one origin, as in production behind Caddy. Seed accounts (password `preclass-demo`, dev only):
`gv.dia@preclass.local` (teacher), `reviewer@preclass.local`, `admin@preclass.local`, `HS10-01…15`, `HS11-01…15`.

## Checks

CI runs `pnpm lint/typecheck/test/build` at the repo root (needs `pnpm` on PATH, e.g. `corepack enable`). Without it:

```bash
cd apps/web
corepack pnpm@10 lint && corepack pnpm@10 typecheck && corepack pnpm@10 test && corepack pnpm@10 build
corepack pnpm@10 test:e2e   # needs API + dev server running; changes seed data
```

E2E runs at 390, 768 and 1280 px; screenshots go to `test-results/screens/` (not committed).

## Screens

| Route | Screen |
|---|---|
| `/login` | Login (email or student code) |
| `/sources`, `/sources/[id]` | S01 Source Library: paste text / upload DOCX, new revision, anchors |
| `/lessons`, `/lessons/new` | Lesson list, create lesson from pinned source revisions |
| `/lessons/[id]?tab=editor` | S02 Generate (async job + polling) and S03 Editor + Source Inspector, provenance editing, switch to newer sources |
| `/lessons/[id]?tab=review` | S04 Review Queue: evidence first, hash-bound approve / request changes / reject, no bulk approve |
| `/lessons/[id]?tab=publish` | S05 Publish Gate (checklist + explicit confirmation), assign to class, withdraw |
| `/lessons/[id]?tab=history` | S06 Version History, new revision from a published one |
| `/classes` | Class assignments and aggregate progress |
| `/student`, `/student/assignments/[id]` | S07 Student view (mobile first): answer first, then the approved explanation |
| `/admin/audit` | Audit log (admin) |

UI rules from `docs/api/API_GUIDE.md` that the code relies on: review status and source evidence are shown as separate
badges (having a source ≠ correct); AI blocks without a source show `noSourceReason`; errors branch on `code`; students
never request provenance, answers or explanations before submitting.

## Layout

- `app/`: routes only (route groups `(teacher)`, `(student)`, `(admin)` apply role guards).
- `src/lib/`: API wrapper and errors, auth context, labels, block tree helpers, formatting.
- `src/features/`: screen building blocks (editor, inspector, review, publish, history, generate, sources).
- `src/components/`: shared UI primitives and badges.
- `tests/`: Vitest unit tests; `tests/e2e/`: Playwright.

## Docker

`docker build -f apps/web/Dockerfile -t preclass-web .` from the repo root (standalone Next server on :3000).
