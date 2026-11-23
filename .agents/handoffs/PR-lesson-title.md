# Handoff: renaming a lesson, grade 12 (branch `feat/lesson-title`, not pushed)

## Where the student-visible name comes from

`StudentAssignmentOut.title` = `assignment.display_title` if set, else `published_version.snapshot["title"]`. The snapshot is
immutable (trigger), so it never changes after publish. Mutable: `lesson.title`, `lesson.goal`, `assignment.display_title`.

## Migrations

- `0015_lesson_title`: `assignment.display_title`, `lesson.lesson_plan_id` (stable link plan to lesson, replaces the title match
  in `_lesson_of`; backfilled by title), table `rename_log` (append-only trigger). Additive.
- `0016_grade_12`: `ck_class_grade` and `ck_lesson_grade` widen to `(10, 11, 12)`. Only loosens, no row changes. Downgrade
  restores the old check as `NOT VALID` so existing grade-12 rows do not block it.
- Run `alembic upgrade head` BEFORE starting the new API (grade 12 and rename both need it).

## Env

None new.

## API / UI

- `PATCH /v1/lessons/{id}` `{title?, goal?}` (owner only, title 3 to 120 trimmed, history event RENAME, rows in `rename_log`).
- `PATCH` assignment accepts `displayTitle` (null clears it). `AssignmentOut` has `displayTitle` and `studentTitle`.
- Teacher UI: "Tên bài" and "Mục tiêu" form on "Soạn & nguồn"; "Đổi tên hiển thị" per assignment on "Lớp & bài giao".
- Default lesson title from a plan: plan title, first letter capital, no "Chuẩn bị:" prefix.
- `assignment_for_lesson` (guest flow) now skips cancelled assignments and takes the latest `open_at`.
- Grade 12: schemas, lesson form select, seed. `Môn Địa lí 12` in a plan sets grade 12 (parser already read 10/11/12).

## Scripts (`scripts/ops/ks_class.py`, run in `apps/api`: `PYTHONPATH=. uv run python ../../scripts/ops/ks_class.py ...`)

- No flags: read-only report of the guest class and gv01's classes.
- `--retitle "<new>" --lesson-title-like "Chuẩn bị: Giáo án"`: dry run. Add `--apply`, then type `RETITLE`. One transaction, writes
  `lesson.title`, `assignment.display_title` and `rename_log` rows (actor `ops:<os user>`). Never edits the snapshot.
- `--create-class 12A1 --grade 12 --teacher gv01@preclass.local`: dry run. Add `--apply`, then type `CLASS`. Needs migration 0016.
  Uses the same id as the seed (`uid("class:12A1")`); an existing class with that code is left alone.
- Production order: `alembic upgrade head`, then the class script, then the retitle script.

## Seed

`seed/accounts.py::ensure_class_12`: class 12A1 for gv01 (empty), idempotent, runs with the demo accounts (never in production).
10A1 and 11A1 are unchanged.

## Risks

- Renaming a published lesson does not change what students see unless the assignment's `display_title` is set (the UI says so).
- Dev DB has duplicate KS assignments for `dan-so-vung`; guests now get the newest open one.
- `rename_log` is append-only: a wrong rename is fixed by renaming again.

## Khôi's two commits on main (9f35635 "update", f911a0d "chỉnh chút"), web only

Student garden (mascot, 7 stages x 6 species, picker, guided tour, FAQ chat, dark/light theme, streak by finished assignments).
No API, migration or backend test touched. Review notes:

- All `localStorage`/`sessionStorage` use in `garden/store.ts`, `lib/theme.tsx`, `companion.tsx` is in try/catch.
- `faq.ts`: claims checked against the API (one submit per question, practice allowed after due, no submit after due, streak
  rule). No answer promises or hints a solution. No em dash. The mascot says "mình", the student is "em".
- The student "3 bước bắt đầu" box was replaced by Khôi's tour; teachers still have it. One of them per role.
- HabitBar no longer shows "Mục tiêu hôm nay" (daily goal); it shows what is left in the assignment (streak = finished assignments).
- Still present: 85dvh sheet on phones, "Gợi ý <mức> · còn k lượt", 10 hints, source refs, "Mở thẻ ôn" button.
- His e2e were broken by the first-visit seed picker (a modal that blocks clicks). Fixed in `tests/e2e/helpers.ts::login`
  (remember "Để sau" for the session). `habit.spec.ts` now also checks that the remaining count goes down by one.
