# Repository Guidelines

## Project Structure & Module Organization

`README.md` is the entry point. Application source is under `apps/web/`; design, planning, research, security, and operations material lives in `docs/`. The repository layout is documented in `docs/02-system-architecture-design.md`:

- `apps/web/`: Next.js full-stack application
- `apps/web/app/`: routes, pages, and API route handlers
- `apps/web/src/`: `core`, `learning`, `ai`, `teacher`, `db`, and shared `ui` modules
- `apps/web/tests/`: Vitest and Playwright tests
- `content/`: lesson packages and evaluation cases
- `drizzle/`: database migrations
- `infra/`: Docker Compose, Caddy, backup, and load-test configuration
- `.agents/skills/`: project-local reusable skills shared by coding harnesses

When adding implementation code, keep route handlers thin, place business logic in services, and access repositories through services. Keep API contracts and architectural decisions in `docs/`.

## Build, Test, and Development Commands

No executable application, package manifest, or build script exists yet, so there are currently no repository-local build or test commands. Once the planned app is added, document the canonical commands here and in the README. The planned workflow is:

```text
pnpm lint
pnpm typecheck
pnpm test
pnpm test:e2e
pnpm build
```

CI is expected to run linting, type checking, unit/integration tests, image builds, secret scanning, and dependency auditing.

## Coding Style & Naming Conventions

Use TypeScript with `strict: true`, two-space indentation, and the project’s configured formatter/linter. Use kebab-case for route directories, descriptive lower-case module filenames (for example, `revisions.service.ts`), PascalCase for React components, and camelCase for variables and functions. Validate API inputs and outputs with Zod.

## Testing Guidelines

The planned stack is Vitest with Testing Library for unit/component tests and Playwright for end-to-end tests across 390, 768, and 1280px viewports. Integration tests should use PostgreSQL/Testcontainers rather than mocking database behavior. Add tests beside the module in `__tests__/` and name them after the behavior under test.

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
