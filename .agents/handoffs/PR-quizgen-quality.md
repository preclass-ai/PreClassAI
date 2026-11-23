# Handoff: quizgen quality (branch `fix/quizgen-quality`)

Trial with a real plan (CV 5512, German industrial practice lesson) showed the AI drafts asked about class procedure, used figures
from elsewhere in the plan, and printed sentence ids. Seven items, priority order 5, 1, 3, 4, 2, 7, 6.

## 5. Bulk approval (state before the change, then the fix)

- Before: `approve_all` (`app/publish/__init__.py`) approved every `AUTO_CHECKED` block with no failed rule, whatever its
  `transformation`. Blocks the AI drafted (`AI_PROPOSED`: AI questions built from a plan, generated lessons, the seed) were bulk approved.
- The plan level (`plan_ai_item`, `origin=ai_generated`) never had a bulk path: only `PATCH .../ai-items/{id}`, one item per call.
  "N cần xác nhận" already excluded rejected items. New test `test_needs_confirmation_count_follows_each_decision` pins the count.
- Now: `approve_all` skips `AI_PROPOSED` blocks and reports them in `skippedAi`. They stay approvable one by one.
  Tests: `test_approve_all_never_approves_ai_proposed_blocks` (test_blocks.py). The only bulk path in OpenAPI is still `approve-all`.
- Behaviour change to confirm with the teacher (K3 asked for "approve all clean blocks"): a generated lesson is mostly `AI_PROPOSED`,
  so "Duyệt tất cả" now approves little there. The confirm dialog says why.

## 1. Knowledge-only input

`quizgen.passages()` decides what the model sees; each numbered sentence keeps its kind (`Source.kinds`: muc_tieu, noi_dung, bang,
cau_hoi, ket_luan; counted in `ai_stats.input`). Kept: knowledge objectives, activity content, tables, questions, step "Kết luận,
nhận định". Left out: equipment, competencies and qualities (group lines such as "a) Năng lực chung:"), products, hand-over, group
work, steps 1 to 3, lines naming Padlet/Zalo/digital or AI competency. Validator `procedural` drops a question about running the
class (reason `procedural`). The bare word "nhóm" is not a trigger ("nhóm tuổi" is geography); only contextual forms are.
Prompt says the question tests Geography knowledge or skill, not how the lesson is organised.

## 2. Figures from the cited quote

`check_question`: every figure in stem and all four options must be in `source_quote` (the cited sentences), else
`number_not_in_quote`. The old plan-wide check stays first. Consequence: a numeric MCQ needs distractors that use figures from the same
sentences; the model is told so.

## 3. Sentence ids

`clean_refs()` turns `[3]`, `[S3]`, "mục [3]", "theo [S3]" into "theo giáo án" (capitalised at a sentence start). Applied in the
model validators (before storing), in `clean_payload` (API output and `build_lesson`, so drafts stored earlier are cleaned too).

## 4. MCQ parser

`structure.SECTION_CUT`: the last option ends at `c) Sản phẩm`, `d) Tổ chức thực hiện`, `Hoạt động`, `Bước n` or a lowercase
`x) ` followed by a capital. The cut tail is dropped, not turned into its own anchor.

## 7. Choosing the parts (national exam format from 2025)

- `POST /lesson-plans/{id}/ai-items/regenerate` takes an optional body `{mcq, numeric, level}` (defaults 6, 2, none); total over
  `QUIZ_GEN_PER_LESSON` gives 422 `QUIZ_COUNT`. After an upload the automatic draft is unchanged (multiple choice only).
- Part I = existing MCQ. Part III = existing `NUMERIC` item type: `AiNumeric` has `op` + `operands`; the server recomputes with
  `validation.derive`, drops a wrong answer (`answer_mismatch`), requires operands and stem figures in the quote, and stores its own
  result. Editing a numeric draft is re-checked. `build_lesson` writes `answer_key{value, unit, tolerance, derivation}`.
- Part II (four true/false statements): NOT added. There is no item type for it (`ItemType` = MCQ, SHORT, NUMERIC). Adding it needs a new
  item type, grading and student UI, so it is a separate decision.
- Level (Nhận biết / Thông hiểu / Vận dụng) is `level` on the draft and on `worksheet_item` payloads; the teacher edits it in the
  draft form and in the block editor. It is a label only.
- No migration: numeric drafts are `kind=quiz` rows with `payload.item_type = NUMERIC`.

## 6. Objectives

`splitObjectives()` (web): lines such as "a) Năng lực chung:" or "2. Phẩm chất" are headings; text after the colon is the first bullet.
The parser still stores these lines as objective rows (they also produce competency tags); only the display changed.

## Known, not fixed

- `structure._head_start` contains literal backspace characters instead of `\b` in `r"…ngay soan…"` (pre-existing, so that branch
  never matches; lessons are split by `Tiết PPCT`). Not touched: fixing it changes how multi-lesson files split.
- The dev database `preclass` was at revision 0012 and lacked `assignment.cancelled_at`; `alembic upgrade head` (to 0014) was run
  before the e2e. Nothing was re-seeded.
- E2E does not exercise the new options panel (counts and level); covered by API integration tests and typecheck only.

## Verification

ruff, `mypy --strict app`, pytest (full), vitest, tsc, eslint; e2e `ai-quiz` (desktop-1280, mobile-390), `publish-flow`, `habit` (desktop-1280).
OpenAPI and `schema.d.ts` regenerated.
