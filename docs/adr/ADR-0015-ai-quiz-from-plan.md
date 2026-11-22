# ADR-0015: AI drafts questions and quick-review cards from a lesson plan

Status: accepted (branch `feat/ai-quiz-from-plan`). Builds on ADR-0012 (Habit) and ADR-0014 (lesson plans CV 5512).

## Decision

After a plan is read, a background step asks the chat model (`CHAT_LLM_*`, same client and fallback model as Habit) for:

- multiple-choice questions, only for a plan with fewer than `QUIZ_GEN_MIN_MCQ` (5) extracted MCQ, `QUIZ_GEN_PER_LESSON` (8) per plan;
- 4 to 6 quick-review cards with a not-scored true/false self-check.

The model sees only the plan's own text (objectives, knowledge, activities; names and signatures already removed at parse time,
phones, emails and addresses removed again). Every draft is checked before it is stored: strict Pydantic schema, four distinct
options, `source_quote` found in the plan (exact or 80% of word triples), every number of the stem and correct option present
in the plan, hints do not leak the answer (the existing `rules.leak` guard). A failing draft is dropped and counted; a broken
JSON reply is retried once.

Drafts live in `plan_ai_item` (`origin=ai_generated`, `status=draft`, `needs_confirmation=true`, `source_quote`). They reach
students only when the teacher approves an item AND builds the lesson: `build_lesson` writes approved items as `AI_PROPOSED`
blocks (`worksheet_item` with fixed `hints`, or the new `review_card` kind), which still go through block-by-block review, the
validation rules and the publish gate. The model never approves or publishes anything.

## Budget and failure

`QUIZ_GEN_DAILY_TOKENS` (100 000) is its own budget (sum of `lesson_plan.ai_tokens` since local midnight); over budget, no model,
too little text or any model error leaves the plan fully usable (`ai_state` skipped or failed, reason in `ai_stats`). One job at a
time, `QUIZ_GEN_TIMEOUT_S` per plan, a restart marks queued/running work failed. `QUIZ_GEN_MOCK` is a dev and test stand-in.

## Habit and student flow

- Chat limits move to env: `CHAT_MAX_MSGS_PER_ITEM` (20), `CHAT_MAX_MSGS_PER_DAY` (100), typed questions only. Hint presses have
  `HINT_MAX_PER_ITEM` (10). Hints 1 to 3 are fixed for AI-drafted questions; 4 to 10 come from the model behind the same guards,
  fallback is the last hint plus a pointer to the source. Replies carry `source` llm|rule|guard; each rule fallback in llm mode is logged.
- A lesson with approved review cards has two steps, "1. Ôn nhanh" then "2. Làm bài kiểm tra". The student answers "Em đã học bài
  này chưa?" once. Progress (`review_progress`) is the learning memory Habit reads to point at a card ("Mở thẻ ôn"). No cards: the
  flow is the quiz alone, as before.
- Insights show review rate and mean correct per group only when both groups have at least 5 students, labelled correlation.

## Consequences and limits

- Items must be approved before "Tạo bài chuẩn bị"; after that the drafts are frozen (edit the lesson itself).
- "Reviewed" in insights means the student opened at least one card, not that it happened before the first answer.
- Migration 0012 is additive (two tables, four columns, and the `chat_message.hint_level` check widened from 3 to 30).
- Quality of the real model's drafts is measured with `scripts/ops/quizgen_real_run.py` (prints counts only, never plan text).
