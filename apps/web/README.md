# Web application

Planned Next.js full-stack application. Keep route handlers thin:

```text
Route Handler → Zod schema → service → repository → PostgreSQL
```

## Module boundaries

- `app/`: routes, pages, and API route handlers only.
- `src/core/`: auth, access control, audit, feature flags, and problem responses.
- `src/learning/`: lessons, sessions, revisions, and transfer state machine.
- `src/ai/`: prompt building, guardrails, provider adapter, quota, and evals.
- `src/teacher/`: progress, stuck points, and report locks.
- `src/db/`: Drizzle schema, migrations adapter, and repositories.
- `src/ui/`: shared components, design tokens, and accessibility primitives.
- `tests/`: unit, integration, and browser tests.
