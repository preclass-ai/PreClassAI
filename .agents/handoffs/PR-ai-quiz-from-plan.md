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
7. Results CSV: one endpoint, `GET /classes/{id}/assignments/{aid}/results.csv` (the "Tải bảng kết quả" button on the class page, from the teacher-results-export PR). This branch added the columns total hints, reviewed before the quiz, and hints per item. The earlier `insights/results.csv` endpoint was removed in the merge of origin/main. Retries do not exist (one attempt per item), so there is no retry column. No survey code, no chat text.
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
| `QUIZ_GEN_ENABLED` | false | Draft questions and review cards after a plan is read. Needs `CHAT_LLM_BASE_URL` and `CHAT_LLM_API_KEY`. |
| `QUIZ_GEN_MODEL` / `QUIZ_GEN_MODEL_FALLBACK` | `openai/gpt-oss-120b` / `qwen/qwen3.8-27b` | Model pair for quiz and review drafting. Chat keeps `CHAT_LLM_MODEL`. |
| `QUIZ_GEN_PER_LESSON` | 8 | Questions per plan. |
| `QUIZ_GEN_MIN_MCQ` | 5 | A plan with fewer extracted MCQ gets drafted questions (review cards are always drafted). |
| `QUIZ_GEN_DAILY_TOKENS` | 100000 | Own daily token budget; over budget the step is skipped (`aiState=skipped`). |
| `QUIZ_GEN_TIMEOUT_S` | 240 | Time limit per plan. |
| `QUIZ_GEN_GAP_S` | 20 | Pause between the quiz call and the review call of one plan (the provider limits tokens per minute). Skipped in mock mode. |
| `QUIZ_GEN_MOCK` | false | Stand-in model built from the plan text. Dev and e2e only, never on a real server. |
| `GUEST_CREATE_PER_IP` | 200 | Guests one IP may create per 10 minutes (a classroom shares one Wi-Fi). Replaces `GUEST_CREATE_PER_HOUR` (was 60 per hour), which is no longer read. Over the limit: 429 `GUEST_BUSY`. |

Removed: `CHAT_MAX_PER_DAY_PER_STUDENT`, `CHAT_MAX_PER_ITEM`, `GUEST_CREATE_PER_HOUR`. Set `GUEST_CREATE_PER_IP` wherever `GUEST_CREATE_PER_HOUR` was set (cloud docs updated). Existing unchanged: `CHAT_ENABLED`, `CHAT_MODE`, `CHAT_LLM_*`, `CHAT_DAILY_TOKEN_BUDGET`.

## Migration and ops

- `0012_ai_quiz`: additive. Columns `lesson_plan.ai_state/ai_stats/ai_tokens/ai_at`, tables `plan_ai_item` and `review_progress`; `chat_message.hint_level` check widened from 0..3 to 0..30. Downgrade drops the tables and columns and restores the old check as NOT VALID.
- `0013_assign_practice`: additive. `assignment.cancelled_at` (soft cancel) and table `practice_attempt` (append-only trigger). Downgrade drops both. Run `alembic upgrade head` before deploying the API.
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
- The CSV "Ôn trước khi làm" column says `Bài không có thẻ ôn` for lessons without review cards.

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

## After the merge with main (22/11/2026): new in this branch
- **Dependency:** `tzdata` in `apps/api/pyproject.toml` and `uv.lock`. `ZoneInfo("Asia/Ho_Chi_Minh")` (class results CSV) no longer needs `/usr/share/zoneinfo`; the Docker image (`python:3.12-slim`, `uv sync --frozen`) gets the zone data from the package. Checked with `PYTHONTZPATH=/nonexistent`.
- **Rate limits (in memory, one API process):** teacher and student logins 10 wrong tries per 5 minutes per account (the judges share one demo account); admin 3 per 15 minutes; guest resume 20 wrong tries per survey code per 10 minutes plus 300 wrong codes in total per 10 minutes; guest creation 200 per IP per 10 minutes (`GUEST_BUSY`). Login errors say "Em nhập sai nhiều lần, thử lại sau ít phút nhé."
- **API changes:** `PATCH` and `DELETE /classes/{id}/assignments/{aid}`, `GET /lessons/{id}/assignments`, `POST /student/assignments/{id}/practice`. `GET /admin/survey/stats`: field `createPerHourPerIp` is now `createPerIp` (admin only; nothing in the web app reads it).
- **Hints:** `GET`/`POST` unchanged. Names by number (1-3 nhẹ, 4-7 rõ hơn, 8-10 chi tiết); `rules.read_where` points at rows and column by name, never a value or an option.
- **Results CSV:** one endpoint (`results.csv` of the class assignment). Columns: code, status, counts, total hints, total redo, reviewed before, last answer, then per item answer, result, hints, redo. No survey code, no chat text.

## Second merge with main and teacher feedback (23/11/2026)
- **Merge:** origin/main (Thiện, web only: login survey code, numeric answer validation, tagline) merged without rebase. Conflicts in `login/page.tsx` and the student answer form: kept both (his numeric check + the branch's "Làm lại"). No migration from main, so the branch migrations stay **0012, 0013 and the new 0014**.
- **Migration `0014_edit_log`:** additive; `transformation_event.before_payload` and `after_payload` (JSONB). Run `alembic upgrade head` before deploying the API. Edits made before it have null before/after.
- **New env:** `GUEST_CREATE_PER_IP` (200 per 10 min per IP, code `GUEST_BUSY`), `QUIZ_GEN_MODEL` (default `openai/gpt-oss-120b`) and `QUIZ_GEN_MODEL_FALLBACK` (default `qwen/qwen3.8-27b`) for quiz and review drafting; they use the chat base URL and key (`CHAT_LLM_BASE_URL`, `CHAT_LLM_API_KEY`). Chat keeps `CHAT_LLM_MODEL` (+ `_FALLBACK`). Also from before: `QUIZ_GEN_ENABLED`, `QUIZ_GEN_MOCK`, `QUIZ_GEN_PER_LESSON`, `QUIZ_GEN_DAILY_TOKENS`, `QUIZ_GEN_TIMEOUT_S`, `QUIZ_GEN_GAP_S`, `CHAT_ENABLED`, `PERSONALIZATION_ENABLED`.
- **Quiz drafting:** each card is parsed alone; extra keys are ignored; `points` 2-5, 3 to 5 hints (first 3 kept); a reply with nothing usable is retried once with the failing field NAMES (logged, never content). `scripts/ops/quizgen_real_run.py` prints the quiz/review model pair.
- **Chat guard:** unit constants (100, 1000, 1.000.000) and 0-100 next to a percent sign are allowed. When the model is blocked or down for a question that matched no keyword, the student gets a how-to hint, not "nằm ngoài bài học".
- **Teacher feedback (Khang):** K1 assignment title in "Lớp & bài giao" opens that assignment's progress (`?class=&assignment=`; "Mở bài học" is the lesson link). K2 history shows who edited, when, and before/after (`before`, `after`, `actorName`, `blockKind` on history events). K3 `POST /revisions/{id}/approve-all {confirm}`: counts first, approves only AUTO_CHECKED blocks with no failed rule, one review event per block. This replaces the old "no bulk approve" rule (PR-02) for clean blocks only. K4 "Tiếp: ..." buttons (sources, editor, review, publish), disabled with a reason. K5 assign asks to confirm when the lesson day is on or before the due day. K6 gate wording "Thầy/cô đã duyệt tất cả các nguồn cần duyệt" (I applied it to the ALL_APPROVED check; confirm with Khang that this was the sentence meant), competency shows "Không bắt buộc" (the publish gate does not check it), no "DỮ LIỆU MINH HỌA" in seed, API examples or e2e titles.
- **Left for after the contest (Khang's wider feedback):** not done in this branch; see the original feedback list with Khang. Not touched: "Tiếp" button after Giao bài (the assign panel already links to progress), per-class bulk assign.
- **Extra risks:** approve-all trusts the server-side validation; a rule that does not exist yet cannot hold a block back. The history keeps full block text before and after (teacher content, not student data). Real-model quizgen with the new pair has not been run yet.

## Risks to know
- Account-based limits let someone lock an account for 5 minutes by typing wrong passwords on purpose.
- The total ceiling on wrong guest codes (300 per 10 minutes) is global: a burst of wrong codes from many students could lock "resume" for everyone for a short time.
- Limits live in memory: a restart resets them, and a second API process would double them.
- `openapi.json` and `schema.d.ts` match the code at the last commit only; commits in between may differ.
- The real-model run (`scripts/ops/llm_smoke.py`, `quizgen_real_run.py`) has not been done after the prompt changes.
- E2E needs `PERSONALIZATION_ENABLED=true` on the API as well as `CHAT_ENABLED`, `QUIZ_GEN_ENABLED`, `QUIZ_GEN_MOCK`. Only student HS10-09 is free for new write specs.
