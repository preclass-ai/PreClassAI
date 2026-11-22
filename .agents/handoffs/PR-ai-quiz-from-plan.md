# Handoff: AI quiz and quick review from a lesson plan

Branch `feat/ai-quiz-from-plan`, rebased on `origin/main` (cd2de17, which already holds `62bb974` and `7cfb945`). Not pushed.
Decision record: `docs/adr/ADR-0015-ai-quiz-from-plan.md`. `apps/api/app/sources/formats.py` has the `timeout_s <= 0` branch (fix `7cfb945`).

## What changed

1. API: migration 0012, `app/lessonplan/quizgen.py` (drafting + validators), plan endpoints `ai-items` (list, patch, regenerate), `review_card` block kind, student review progress.
2. Teacher UI: plan card status, review screen with tabs Câu hỏi / Ôn tập, label "AI soạn", source quote, Sửa / Duyệt / Loại.
3. Habit: chat limits from env, hint limit 10, reply `source` (llm|rule|guard), log of each rule fallback, "Mở thẻ ôn".
4. HABIT AI sheet on phones (part E).
5. Student flow "1. Ôn nhanh" then "2. Làm bài kiểm tra"; insights review impact (needs 5 students per group).
6. After a student submits: right answer, explanation and "Theo giáo án: <quote>" (AI-drafted questions carry `sourceQuote` in the item payload) or "Nguồn: tài liệu giáo viên đã duyệt".
7. Insights: "Tải bảng số liệu (CSV)" per assignment (`GET .../insights/results.csv`): anonymous code, right/wrong and hints per item, reviewed or not, last submit time, then totals (completion, rate per item and per skill). UTF-8 with BOM, no chat text.
8. `/du-lieu` states that the plan text (names and signatures removed) goes to the AI service and that the teacher approves before students see anything.
9. ESLint ignores `.next-e2e/`.

### Regression found and fixed: habit-panel 63 vs 64

`habit-panel.spec` at 1280 failed (panel top 63, header bottom 65). Green on `origin/main`, red on this branch, so it was this branch: the review link used the class `.link-btn`, which already exists (the logout button in the header uses it), and my rule made the header taller. Fixed by a separate class `.review-link` (commit "fix(web): do not redefine .link-btn ...").

## Environment variables (names as in `apps/api/app/config.py`)

| Variable | Default | Meaning |
|---|---|---|
| `CHAT_MAX_MSGS_PER_ITEM` | 20 | Typed questions per student per question. Hint presses do not count. |
| `CHAT_MAX_MSGS_PER_DAY` | 100 | Typed questions per student per day. |
| `HINT_MAX_PER_ITEM` | 10 | Hint presses per question (429 `HINT_LIMIT`). |
| `QUIZ_GEN_ENABLED` | false | Draft questions and review cards after a plan is read. Needs `CHAT_LLM_*`. |
| `QUIZ_GEN_PER_LESSON` | 8 | Questions per plan. |
| `QUIZ_GEN_MIN_MCQ` | 5 | A plan with fewer extracted MCQ gets drafted questions (review cards are always drafted). |
| `QUIZ_GEN_DAILY_TOKENS` | 100000 | Own daily token budget; over budget the step is skipped (`aiState=skipped`). |
| `QUIZ_GEN_TIMEOUT_S` | 240 | Time limit per plan. |
| `QUIZ_GEN_GAP_S` | 20 | Pause between the quiz call and the review call of one plan (the provider limits tokens per minute). Skipped in mock mode. |
| `QUIZ_GEN_MOCK` | false | Stand-in model built from the plan text. Dev and e2e only, never on a real server. |

Removed: `CHAT_MAX_PER_DAY_PER_STUDENT`, `CHAT_MAX_PER_ITEM`. Existing unchanged: `CHAT_ENABLED`, `CHAT_MODE`, `CHAT_LLM_*`, `CHAT_DAILY_TOKEN_BUDGET`.

## Migration and ops

- `0012_ai_quiz`: additive. Columns `lesson_plan.ai_state/ai_stats/ai_tokens/ai_at`, tables `plan_ai_item` and `review_progress`; `chat_message.hint_level` check widened from 0..3 to 0..30. Downgrade drops the tables and columns and restores the old check as NOT VALID.
- Old label in an existing database: `cd apps/api; uv run python ../../scripts/ops/fix_seed_label.py` (dry run, default) then `... --apply`. It rewrites only `source_asset.title/license_note` and `lesson.title`; immutable rows (anchors, snapshots, approved blocks) are only counted.
- Real-model numbers: `uv run python ../../scripts/ops/quizgen_real_run.py "<plan>" --lesson 1` with `CHAT_LLM_*` set. Prints counts only. Not run yet (the key file could not be read in the agent session).

## Verify

```text
cd apps/api && uv run ruff check . && uv run mypy --strict app && uv run pytest
cd apps/web && pnpm lint && pnpm typecheck && pnpm test
VERCEL=1 API_ORIGIN=https://x.example.com pnpm build      # Windows cannot create the standalone symlinks
# e2e: API with CHAT_ENABLED=true PERSONALIZATION_ENABLED=true QUIZ_GEN_ENABLED=true QUIZ_GEN_MOCK=true on a freshly seeded DB
E2E_BASE_URL=... pnpm exec playwright test
```

## Remaining limits

- Drafts must be approved before "Tạo bài chuẩn bị"; afterwards they are frozen (edit the lesson itself).
- "Reviewed" means the student opened at least one card, not that it happened before the first answer.
- The real model's draft quality is unmeasured; the e2e uses the mock model.
- Hints 4 to 10 depend on `CHAT_MODE=llm`; in rule mode they repeat hint 3 plus a pointer to the source.
- The CSV "ôn trước" column says `khong_co_bai_on` for lessons without review cards.

## Real-model run findings (Groq), and the fix

- Lesson 2: quiz 7/10 valid. Review: qwen failed with `ProviderHTTPError`, the gpt-oss-120b fallback wrote 5 cards, all rejected as `quote_not_in_plan`.
- Provider errors now carry `status` and `detail` (at most 200 characters: JSON `code`, `type`, `message` only, never `failed_generation`, key masked). `OpenAIChat` records which model failed first (`attempts`, "model:status"); the script prints it.
- Rate limit or 5xx (429, 500, 502, 503) is retried once after the wait the provider asked for (capped at 30 s, 12 s if unsaid). 400, 401 and timeouts are not retried.
- `max_tokens` of the review call went from 3000 to 1800 and quiz from 4000 to 3500: the provider counts it toward the per-minute token limit, together with the plan text sent twice (quiz, then review).
- Quotes: both sides are folded (NFC, soft hyphens, hyphen and newline as a word break, spaces, case, accents) and a quote of 30 characters or more passes at a 90% partial match (difflib, no new dependency). The review prompt now requires one sentence copied word for word; `points` is the rewritten part.
- A failed review no longer costs the quiz: each kind is saved on its own, the failed kind is marked in `aiStats` (`failed`, `reason`, `status`), the screen says "Chưa soạn được thẻ ôn", and "Tạo lại câu hỏi" redoes only the failed kind.

## Sentence ids instead of quotes (after the second real run)

The real run showed models rewrite quotes (best match scores 67 to 89). The prompt now numbers the plan sentences `[S1]..[Sn]` (cut at line breaks and . ! ?, pieces under 15 characters dropped) and asks for `source_sentence_ids` (1 to 3 numbers). The server joins those sentences into `source_quote`, so a quote is verbatim by construction; an unknown id is rejected (`bad_sentence_id`). A model that sends text anyway falls back to the fuzzy match, now at 85. Numbers must still appear in the plan.

- `QUIZ_GEN_GAP_S` (20): wait between the quiz and review calls of one plan. Jobs run one at a time (an in-process lock, FIFO).
- A 429 on a long job waits the time the provider asked for and retries the SAME model once before the fallback is tried.
- Prompt budget 6000 tokens (estimate: characters / 3). Over it, appendix and rubric sentences are cut first, then the tail. `max_tokens`: quiz 3000, review 1300.
- Default `QUIZ_GEN_TIMEOUT_S` is now 240 because of the gap.
