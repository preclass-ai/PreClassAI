# Handoff: AI quiz and quick review from a lesson plan

Branch `feat/ai-quiz-from-plan` (from `origin/main`, plus cherry-pick of `62bb974`: llm mode no longer blocks free questions by keyword).
Decision record: `docs/adr/ADR-0015-ai-quiz-from-plan.md`. Not pushed, not merged, nothing written to any cloud service.

## Commits

1. `feat(api)`: migration 0012, `app/lessonplan/quizgen.py`, endpoints, `review_card` block, student review progress, openapi + client types.
2. `feat(web)`: plan card status, AI review screen (labels, source quote, Sửa / Duyệt / Loại), review card editor.
3. `feat(habit)`: limits from env, hint 10, `source`, fallback log, seed label removed, `scripts/ops/fix_seed_label.py`.
4. `fix(web)`: HABIT AI bottom sheet on phones (part E).
5. Part F: student two-step flow, Habit pointing to review cards, insights review impact, tests.

## Verify

```text
cd apps/api && uv run ruff check . && uv run mypy --strict app && uv run pytest
cd apps/web && pnpm lint && pnpm typecheck && pnpm test      # build locally with VERCEL=1 API_ORIGIN=https://x.example.com (Windows cannot create the standalone symlinks)
E2E_BASE_URL=... pnpm exec playwright test tests/e2e/ai-quiz.spec.ts   # API with CHAT_ENABLED=true QUIZ_GEN_ENABLED=true QUIZ_GEN_MOCK=true
```

## Open

- Real-model run: `scripts/ops/quizgen_real_run.py "<plan>" --lesson 1` with `CHAT_LLM_*` set. Prints counts only.
- Set `QUIZ_GEN_ENABLED=true` (and `CHAT_LLM_*`) on the server to switch the feature on; it is off by default.
- Existing databases: run `scripts/ops/fix_seed_label.py` (dry run first) to remove the old label from titles and notes.
