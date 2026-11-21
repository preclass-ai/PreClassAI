# Data model — PreClass AI backend v2

Nguồn sự thật: `apps/api/app/db/models.py` + migration `apps/api/alembic/versions/0001_*`. Tài liệu này giải thích cho frontend: bảng nào lưu gì, trạng thái nào có thể xuất hiện, và DB chặn những gì. Frontend **không** đọc DB; mọi thứ qua `/v1` (xem `API_GUIDE.md`).

Quy ước: khóa `uuid` (`gen_random_uuid()`), `created_at timestamptz`, enum = `text + CHECK`. Tên cột `snake_case` trong DB, **camelCase** trên API. Toàn bộ dữ liệu seed là **mock, ghi rõ "DỮ LIỆU MINH HỌA"**.

## 1. Sơ đồ quan hệ

```mermaid
erDiagram
  app_user ||--o{ class_member : in
  class ||--o{ class_member : has
  app_user ||--o{ source_asset : owns
  source_asset ||--|{ source_revision : versions
  source_revision ||--|{ source_anchor : anchors
  app_user ||--o{ lesson : authors
  lesson ||--|{ lesson_revision : revisions
  lesson_revision }o--o{ source_revision : lesson_source
  lesson_revision ||--o{ content_block : blocks
  content_block ||--o{ content_block : parent
  content_block ||--o{ provenance_link : sourced_by
  source_anchor ||--o{ provenance_link : cited_by
  content_block ||--o{ block_dependency : depends
  content_block ||--o{ transformation_event : history
  content_block ||--o{ validation_result : checks
  content_block ||--o{ review_event : reviews
  lesson_revision ||--o| published_version : publishes
  published_version ||--o{ assignment : assigned
  class ||--o{ assignment : receives
  assignment ||--o{ student_attempt : answers
```

## 2. Bảng

| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `app_user` | `email` hoặc `login_code`, `display_name`, `role` TEACHER/REVIEWER/STUDENT/ADMIN, `password_hash` (argon2), `is_active` | Học sinh chỉ có `login_code`, không lưu email/SĐT. Khách khảo sát (migration 0002): `is_guest`, `survey_code` (unique, dạng `KS-XXXX`, trùng `login_code`), `last_seen_at`; `password_hash` là giá trị không dùng được; không lưu IP. |
| `session` | `token_hash`, `user_id`, `expires_at`, `revoked_at` | Cookie session phía server; logout thu hồi thật. |
| `class`, `class_member` | `code`, `grade` 10/11; `role_in_class` TEACHER/STUDENT | `UNIQUE(class_id, user_id)`. |
| `source_asset` | `owner_id`, `title`, `license_note`, `visibility` PRIVATE/SCHOOL | SCHOOL cần `license_note` (VAL-09). |
| `source_revision` | `asset_id`, `version`, `sha256`, `mime`, `extract_status`, `locked_at` | `UNIQUE(asset_id, version)`. **Bất biến** (trừ `extract_status`, `locked_at`). |
| `source_anchor` | `source_revision_id`, `code` (`anc_<rev8>_<seq>`), `kind`, `locator`, `excerpt`, `excerpt_hash`, `numbers numeric[]` | **Bất biến.** `locator`: `{para_index}` hoặc `{table,row,col}`. `numbers` do parser số Việt Nam (`.` nghìn, `,` thập phân). |
| `lesson` | `author_id`, `subject` GEOGRAPHY, `grade`, `title`, `goal` | |
| `lesson_revision` | `lesson_id`, `revision_no`, `state`, `base_revision_id`, `version` | `version` = khóa lạc quan (gửi lại khi publish / đổi nguồn). |
| `lesson_source` | `lesson_revision_id`, `source_revision_id` | Nguồn gắn với một revision. |
| `lesson_reviewer` | `lesson_id`, `reviewer_id` | REVIEWER chỉ duyệt bài được gán (cờ cấu hình, mặc định tắt). |
| `content_block` | `revision_id`, `kind`, `parent_id`, `position`, `payload` jsonb, `content_hash`, `transformation`, `review_status`, `no_source_reason`, `is_factual`, `version`, `deleted_at` | Xóa mềm. `version` = khóa lạc quan khi PATCH. |
| `provenance_link` | `block_id`, `anchor_id`, `relation` derived_from/quotes/supports, `rationale`, `status` VERIFIED/UNRESOLVED | VERIFIED chỉ khi anchor thuộc nguồn của revision. |
| `block_dependency` | `block_id`, `depends_on_block_id`, `kind` ANSWER_OF/EXPLANATION_OF/FEEDBACK_OF/LABEL_OF | Sửa X ⇒ block phụ thuộc X (bắc cầu) và cha trực tiếp của X → REVIEW_AGAIN. |
| `transformation_event` | `block_id`, `actor_type`, `actor_id`, `operation`, `before_hash`, `after_hash`, `generator_version` | **Chỉ thêm.** |
| `validation_result` | `block_id`, `rule` VAL-01..09, `severity`, `outcome`, `evidence`, `method`, `content_hash` | **Chỉ thêm.** Kết quả cũ gắn hash cũ → API trả `isCurrent`. |
| `review_event` | `block_id`, `content_hash`, `source_hashes text[]`, `reviewer_id`, `action`, `note` | **Chỉ thêm.** Duyệt gắn hash nội dung + hash nguồn. |
| `generation_job` | `revision_id`, `output_type`, `params`, `status`, `error`, `model`, `prompt_version`, `tokens_in/out` | Tối đa 1 job QUEUED/RUNNING mỗi revision (unique index). |
| `usage_daily` | `day`, `tokens` | Đếm token cho `GENERATION_DAILY_TOKEN_BUDGET`. |
| `published_version` | `lesson_revision_id` UNIQUE, `snapshot` jsonb, `snapshot_hash`, `published_by`, `state` ACTIVE/WITHDRAWN, `withdraw_reason` | **Snapshot bất biến.** Thu hồi là một chiều. |
| `assignment` | `published_version_id`, `class_id`, `open_at`, `due_at` | |
| `student_attempt` | `assignment_id`, `student_id`, `item_block_id`, `answer`, `is_correct`, `request_id` | `UNIQUE(assignment, student, item)`; `is_correct = null` với câu SHORT/rubric. **Không sửa/xóa.** |
| `audit_log` | `actor_id`, `action`, `resource_type`, `resource_id`, `metadata` | **Chỉ thêm**; không chứa nội dung (kể cả `INSPECT_PROVENANCE`). |

## 3. Trạng thái

`lesson_revision.state`: `DRAFT → IN_REVIEW → PUBLISHED → SUPERSEDED` (không quay lại sau PUBLISHED). Sửa bài đã xuất bản = `POST /revisions/{id}/new-revision` → DRAFT mới; bản cũ giữ nguyên.

`content_block.review_status`:

| Giá trị | Nghĩa | UI gợi ý |
|---|---|---|
| `UNREVIEWED` | Vừa sinh/thêm, chưa kiểm | xám |
| `AUTO_CHECKED` | Qua validation tự động, **chưa** có người duyệt | xanh nhạt |
| `FLAGGED` | Có BLOCKER (số lạ, anchor sai, đáp án sai…) | đỏ |
| `APPROVED` | Có người duyệt đúng hash hiện tại | xanh |
| `REVIEW_AGAIN` | Đã duyệt nhưng nội dung/nguồn/khối liên quan đổi | cam |
| `REJECTED` | Bị từ chối | đỏ sẫm |

**Nguồn ≠ đúng (PR-01):** `provenance_link` (có nguồn) và `review_status`/`validation_result` (có đúng không) lưu riêng; UI phải hiển thị tách biệt.

`transformation`: `ORIGINAL` (trích nguyên văn), `PARAPHRASED`, `SYNTHESISED` (tổng hợp nhiều anchor), `AI_PROPOSED` (AI đề xuất, thường kèm `noSourceReason`), `TEACHER_AUTHORED`.

## 4. Payload theo `kind` (JSON camelCase)

| kind | payload | Ghi chú |
|---|---|---|
| `heading`, `paragraph`, `instruction`, `card_front`, `card_back` | `{text}` | |
| `data_fact` | `{label, value: number, unit, period, region, note?}` | Bắt buộc đủ `value, unit, period, region` (PR-07). |
| `worksheet_item` | `{stem, itemType: MCQ\|SHORT\|NUMERIC, skill: READ_TABLE\|COMPARE\|CALCULATE\|EXPLAIN}` | Con: `option`, `answer_key`, `explanation`. |
| `option` | `{label: "A".."D", text}` | Con của `worksheet_item`. |
| `answer_key` | MCQ `{correct}` · NUMERIC `{value, unit, tolerance, derivation?}` · SHORT `{rubricPoints[]}` | |
| `explanation` | `{text, derivation?}` | Phụ thuộc `answer_key` (EXPLANATION_OF). |

`derivation` = `{op: sum\|diff\|ratio\|percent, operands: [anchor code \| number]}` cho số **tính ra** (không nằm nguyên văn trong nguồn); server tính bằng `Decimal` rồi so với payload.

API trả block **phẳng** (`parentId` + `position`); frontend tự dựng cây.

## 5. Hash (ràng buộc duyệt)

- `content_hash = sha256(canonical_json({kind, payload, parent, transformation, noSourceReason}))` (JSON khóa sắp xếp, không khoảng trắng, UTF-8). `parent` = id block cha.
- `review_event.source_hashes` = các `sha256` của `source_revision` và `excerpt_hash` của anchor ở mọi link VERIFIED (sort, unique).
- Duyệt hợp lệ ⇔ sự kiện duyệt **mới nhất** của block là `APPROVE` với `content_hash` bằng hash hiện tại. Client gửi `contentHash` đã thấy; sai → `409 STALE_REVIEW`.
- `published_version.snapshot_hash = sha256(canonical_json(snapshot))`.

## 6. Quy tắc DB tự chặn (kể cả khi code backend sai)

Thông báo lỗi DB bắt đầu bằng tiền tố; service ánh xạ sang mã API.

| Tiền tố | Chặn | Mã API |
|---|---|---|
| `APPEND_ONLY` | UPDATE/DELETE `transformation_event`, `validation_result`, `review_event`, `audit_log`, `student_attempt` | 500 (lỗi lập trình) |
| `IMMUTABLE_SOURCE` | Sửa/xóa `source_anchor`; sửa nội dung `source_revision` | 500 |
| `REVISION_LOCKED` | Thêm/sửa/xóa `content_block`, `provenance_link`, `lesson_source` khi revision PUBLISHED/SUPERSEDED | 409 `REVISION_LOCKED` |
| `NO_HARD_DELETE` | `DELETE content_block` (dùng `deleted_at`) | 500 |
| `APPROVAL_INVALID` | Đặt `APPROVED` khi không có `review_event` APPROVE mới nhất khớp hash hiện tại; sửa hash mà vẫn APPROVED | 409 `STALE_REVIEW` |
| `ANCHOR_NOT_IN_LESSON` | Link VERIFIED tới anchor không thuộc nguồn của revision | 422 `ANCHOR_NOT_IN_LESSON` |
| `SNAPSHOT_IMMUTABLE` | Sửa/xóa `published_version.snapshot` | 500 |
| `INVALID_STATE_TRANSITION` | PUBLISHED → DRAFT/IN_REVIEW; SUPERSEDED → khác; WITHDRAWN → ACTIVE | 409 |

Hai role DB: `preclass_migrator` (chủ schema, chạy migration) và `preclass_app` (không UPDATE/DELETE các bảng chỉ-thêm). Migration tạo role `NOLOGIN`; vận hành đặt `LOGIN PASSWORD` (xem RUNBOOK). Dev chạy bằng user `preclass` (superuser Postgres của container); trigger vẫn áp dụng.

## 7. Dữ liệu seed (mock)

Chạy: `uv run alembic upgrade head && uv run python -m seed.seed` trong `apps/api` (cần `DATABASE_URL`). Mật khẩu mọi tài khoản: `$SEED_PASSWORD`, mặc định `preclass-demo` (**chỉ dev**).

| Tài khoản | Vai trò | Ghi chú |
|---|---|---|
| `gv.dia@preclass.local` | TEACHER | Dạy lớp 10A1 và 11A1; tác giả 5 bài |
| `gv.khac@preclass.local` | TEACHER | Tác giả bài `xuat-khau`; dùng để thử 404 (IDOR) |
| `reviewer@preclass.local` | REVIEWER | |
| `admin@preclass.local` | ADMIN | Xem audit log |
| `HS10-01` … `HS10-15` | STUDENT | Lớp 10A1 |
| `HS11-01` … `HS11-15` | STUDENT | Lớp 11A1 |

| Bài (key) | Lớp | Tác giả | Trạng thái seed |
|---|---|---|---|
| `dan-so-vung` | 10 | gv.dia | **PUBLISHED**, giao cho 10A1; mọi block APPROVED |
| `dien-tich-rung` | 10 | gv.dia | DRAFT, đủ mọi trạng thái: APPROVED, REVIEW_AGAIN (đã sửa sau duyệt), FLAGGED (số lạ `5,5`), REJECTED, UNREVIEWED, AUTO_CHECKED |
| `san-luong-lua`, `gdp-nganh`, `san-luong-dien` | 10/11 | gv.dia | DRAFT, AUTO_CHECKED |
| `xuat-khau` | 11 | gv.khac | DRAFT, AUTO_CHECKED |

Id seed cố định (uuid5), nên trùng với ví dụ trong `openapi.json`: lesson `dan-so-vung` = `712030dc-698a-5be5-9781-5d7a907b3628`, lớp 10A1 = `d97fbc44-edb6-5333-b65d-1427e836354c`, lớp 11A1 = `cf4d05fd-9a71-57a0-9eaa-421c08c3c74c`.

Mỗi bài có: 1 nguồn văn bản (tiêu đề, 2 đoạn, bảng 4 hàng × 2 cột → 11 anchor) và ~19 block: `heading`, 2 `paragraph`, `instruction`, `data_fact`, 1 câu MCQ (4 `option`, `answer_key`, `explanation`), 1 câu NUMERIC (`answer_key` có `derivation`, `explanation`).

## Habit (migration 0003, chỉ thêm)

| Bảng | Cột chính | Ghi chú |
|---|---|---|
| `chat_session` | `id, assignment_id, student_id, item_block_id, created_at` | duy nhất theo (assignment, student, item) |
| `chat_message` | `id, session_id, role user/assistant, action hint/ask/explain, text, hint_level 0..3, mode rule/llm, blocked_reason, tokens_in, tokens_out, request_id, created_at` | **append-only** (trigger `tg_append_only`); `text` đã che PII; duy nhất (session, request_id) cho dòng assistant |
| `study_activity` | `student_id, day, items_answered, hints_used` | khóa chính (student, day); chỉ cập nhật khi `CHAT_ENABLED=true` |

`blocked_reason` ghi cả từ chối (INJECTION, ANSWER_REQUEST, CONFIRM_OPTION, UNSAFE, OFFTOPIC) lẫn lý do rơi về rule của LLM (`LLM_ANSWER, LLM_NUMBER, LLM_PII, LLM_PROMPT, LLM_ERROR, LLM_BUDGET`).

## Cá nhân hóa (migration 0004, chỉ thêm)

| Bảng | Cột | Ghi chú |
|---|---|---|
| `student_preference` | `student_id, key, value on/5/10, updated_at` | khóa chính (student, key); `key` bị CHECK vào đúng 6 khóa cố định; không có hàng = tắt; không có cột nào khác về học sinh |
