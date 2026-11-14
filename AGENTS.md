# Repository Guidelines

## Project Structure & Module Organization

`README.md` is the entry point. Architecture decision: `docs/adr/ADR-0010-fastapi-backend.md` (supersedes the Next.js monolith in `docs/02`). Product spec and plan live in `docs/v2/`.

- `apps/api/`: FastAPI backend (Python 3.12, managed with `uv`); `app/`, `alembic/`, `seed/`, `tests/`, `openapi/openapi.json`
- `apps/web/`: Next.js frontend (owned by Thiện); calls the REST API under `/v1`
- `docs/`: design, planning, security, operations; API guides in `docs/api/`
- `content/`: lesson packages and evaluation cases (real content later)
- `infra/`: Docker Compose, Caddy, backup, and load-test configuration
- `.agents/skills/`: project-local reusable skills shared by coding harnesses

In `apps/api`, keep route handlers thin, place business logic in services, and access repositories through services. Keep API contracts and architectural decisions in `docs/`.

## Build, Test, and Development Commands

Backend (run in `apps/api/`, set `PYTHONUTF8=1` on Windows):

```text
uv sync
uv run ruff check .
uv run mypy --strict app
uv run pytest
docker compose -f ../../infra/compose.dev.yml up -d
```

Frontend (pnpm workspace at the repo root: `apps/web` + `packages/api-client`; use `corepack pnpm@10` if `pnpm` is not installed). See `apps/web/README.md`.

```text
pnpm install
pnpm --filter @preclass/web dev          # :3000, proxies /v1 to API_ORIGIN (default http://localhost:8000)
pnpm lint && pnpm typecheck && pnpm test && pnpm build
pnpm --filter @preclass/web test:e2e     # Playwright at 390/768/1280 px against a running, seeded stack
```

CI runs the Python job and repository policy checks; the pnpm job (`app`) runs when the repository variable `APP_CI_ENABLED=true`.

## Coding Style & Naming Conventions

Backend: Python with `mypy --strict`, `ruff`, type hints everywhere, snake_case; validate API inputs and outputs with Pydantic. Frontend: TypeScript with `strict: true`, two-space indentation, kebab-case route directories, PascalCase React components, camelCase variables; validate with Zod or the generated OpenAPI client.

## Testing Guidelines

Backend: `pytest` with `httpx.AsyncClient`; integration tests use a real PostgreSQL (`TEST_DATABASE_URL`), never a mocked database. Frontend: Vitest with Testing Library and Playwright across 390, 768, and 1280px viewports. Name tests after the behavior under test.

## Commit & Pull Request Guidelines

Use short, imperative commit subjects, consistent with existing history (for example, `Add initial documentation`). Keep commits focused. Pull requests should describe the change, link the relevant task or decision, include test results, and attach screenshots for UI changes. Keep `main` protected: merge only after required review and green CI.

## Security & Configuration

Never commit secrets or real student data. Use mock IDs such as `MOCK-01` in fixtures, keep environment-specific secrets separate, and redact sensitive content from logs. Follow the documented rule that production credentials and infrastructure accounts are owned by the mentor or school.

## Collaboration Contract

`AGENTS.md` is the canonical instruction file for every coding harness. Claude Code reads `CLAUDE.md`; Gemini/Antigravity-compatible harnesses read `GEMINI.md`; both files point back here and must not duplicate policy.

Before editing, read `.agents/README.md` and the task record. Before claiming completion, run the task's verification commands and write a handoff in `.agents/handoffs/`.

When a task matches a listed workflow, read the corresponding project-local skill at `.agents/skills/<skill-name>/SKILL.md`. `docs/tooling/skills.md` is an inventory, not the executable skill content.

Architecture, security, data-processing, deployment, and budget changes require an ADR or an update to the relevant operations document. Do not silently resolve an open Q-/A- decision.

## Operational Entry Points

- Engineering and deployment plan: `docs/07-engineering-operations-plan.md`
- Security documents: `docs/security/`
- Operations runbooks: `docs/operations/`
- Reusable skills and harness mapping: `docs/tooling/skills.md`
- Shared task, decision, and handoff templates: `.agents/`
