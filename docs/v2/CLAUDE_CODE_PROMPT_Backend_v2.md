# PROMPT CHO CLAUDE CODE — Backend PreClass AI v2 (Source-to-Output Traceability)

> **Chạy trong repo PreClassAI có sẵn.** Đọc `AGENTS.md`, `.agents/README.md`, `.agents/tasks/T9-backend-v2.md` trước. Tài liệu đi kèm nằm ở `docs/v2/`.

## Điều chỉnh theo repo (thắng mọi chỗ khác trong prompt khi có mâu thuẫn)

- Làm việc trên branch `feat/backend-v2` (tạo từ `main`). **Không push.** Không đụng `apps/web/` (Thiện làm frontend ở đó).
- Thư mục backend là **`apps/api/`** (không phải `backend/`). Cấu trúc mục 4 đặt bên trong `apps/api/`.
- Tài liệu: `DATA_MODEL.md`, `API_GUIDE.md` → `docs/api/`; `PROGRESS.md`, `DECISIONS_AGENT.md` → `.agents/` ; `HANDOFF.md` → `.agents/handoffs/T9-backend-v2.md` (theo template `.agents/handoffs/handoff-template.md`); `RUNBOOK.md` → cập nhật `docs/operations/`.
- `openapi.json` → `apps/api/openapi/openapi.json`.
- GĐ 1 viết `docs/adr/ADR-0010-fastapi-backend.md` **từ nội dung `.agents/decisions/D-001-backend-v2-direction.md` (đã accepted; không tự quyết lại)**: supersedes ADR-0001 (và một phần 0002/0005/0006/0008 trong `docs/01`). Thêm banner "Superseded by ADR-0010/D-001" đầu `docs/01`, `02`, `05`, `06` và `drizzle/README.md` (không viết lại nội dung). Cập nhật "Build, Test" và "Project Structure" của `AGENTS.md` cho `apps/api/`.
- Docker Compose: mở rộng `infra/compose.{dev,staging,prod}.yml` / `Caddyfile` có sẵn (đọc trước khi sửa), không tạo file compose mới ở gốc. Caddy route `/v1/*` → `api:8000`, còn lại → `web:3000` (cùng origin). Staging/prod: 2 image (`api`, `web`), healthcheck Postgres ở cả staging, `api` ở network `edge` để gọi LLM, tạo `infra/.env.staging.example` và `.env.prod.example`.
- Hợp nhất `.env.example` có sẵn với biến mục 11: **một** `DATABASE_URL` (dạng `postgresql+asyncpg://`), giữ `AI_ENABLED`, `SESSION_SECRET`, `BACKUP_ENCRYPTION_KEY`, bỏ khóa trùng; thêm `TEST_DATABASE_URL`. `.gitignore`: thêm `__pycache__/`, `.venv/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`, `apps/api/data/`.
- CI: thêm job Python vào `.github/workflows/ci.yml`, không xóa job hiện có.
- Máy chạy là **Windows**, Python hệ thống là 3.10 (uv đã có sẵn Python 3.12, **không cần** `uv python install`): **dùng `uv`** (`uv venv --python 3.12`, `uv sync`, `uv run pytest`) trong `apps/api/`, đặt `PYTHONUTF8=1` (console cp1258 làm Python lỗi khi in tiếng Việt), không dùng python hệ thống, lệnh tương thích PowerShell/Git Bash; đặt `.gitattributes` `* text=auto eol=lf` cho file mới nếu cần. Cần Docker Desktop cho Postgres (compose dev). Test đọc `TEST_DATABASE_URL` (DB `preclass_test` trên Postgres của compose; CI dùng service container); Testcontainers là tùy chọn. Nếu Docker không chạy được, ghi vào handoff và dùng Postgres local, không dừng việc.
- Commit theo style repo: tiêu đề ngắn, mệnh lệnh, tiếng Anh (ví dụ `Add FastAPI skeleton`), kèm trailer attribution của harness. Bỏ "Conventional Commits" ở mục 0.

---

## Quyết định D-001 (đã accepted; thắng mọi chỗ khác trong prompt)

Nguồn: `.agents/decisions/D-001-backend-v2-direction.md` (mã Bx/Cx/Dx/Qx tra ở đó).

1. **Lát cắt dọc (Q3).** Thứ tự: hợp đồng → auth → text/DOCX + anchors → **Worksheet end-to-end** (generate Mock → validate → review → publish → student) → AT-01..14 → Flashcards. Hoãn (P0.5, chỉ khi còn giờ): `OpenAICompatibleProvider` thật, diff chi tiết ở history, `/progress`, VAL-08/09 thực chất, pagination cursor cho list nhỏ, Testcontainers bắt buộc, pre-commit/gitleaks cục bộ (gitleaks chạy ở CI). Seed **2 bài** đầy đủ trước GĐ6, đủ 6 bài sau. Đã cắt khỏi đặc tả: Slides, Visual Story, PPTX/PDF/OCR, block `image/callout/slide/story_scene` (ghi vào ADR-0010; Product chưa ack, không chặn mã).
2. **Hợp đồng OpenAPI-first (Q4).** GĐ3 = Pydantic schema + route khai báo (handler 501 hoặc dữ liệu tối thiểu) + `examples` từ fixture tay + Prism. Không làm "stub đọc DB seed". **v0 gửi Thiện tối 14/11; freeze v1 sáng 16/11** (`info.version=1.0.0`); CI chặn đổi tên/xóa field sau freeze. Quy ước lỗi: sai **vai trò** → 403 `FORBIDDEN_ROLE`; sai **sở hữu/lớp** → 404.
3. **Số dẫn xuất (Q5).** Payload có thể mang `derivation: {op: sum|diff|ratio|percent, operands: [anchor alias | số]}`; server tính bằng `Decimal` và đối chiếu; sai → VAL-03 BLOCKER. Parser số Việt Nam duy nhất cho anchors và payload (`.` nghìn, `,` thập phân; `1.234` mơ hồ → chấp nhận cả hai cách đọc), có test bảng riêng. Nếu trễ, rơi về: số trong `answer_key` gắn WARNING.
4. **Auth (Q6).** Cookie session ngẫu nhiên phía server (bảng `session`, `HttpOnly; Secure; SameSite=Lax`), CSRF bằng header tùy chỉnh + kiểm `Origin`, logout thu hồi thật. Cùng origin qua Caddy; dev dùng Next `rewrites`. Thay mục JWT/refresh trong §4. Rate limit đăng nhập.
5. **Bất biến và hash (Q7, B1–B12).** `content_hash = sha256(canonical_json({kind, payload, parent, transformation, noSourceReason}))`; thêm `content_block.version`, `deleted_at` (soft delete, không xóa vật lý); `review_event.source_hashes` = sha256 `source_revision` của mọi link VERIFIED + `excerpt_hash` anchors (sort, unique). Review và publish dùng `SELECT ... FOR UPDATE` + kiểm `version`/hash trong cùng transaction (test song song). Trigger: chặn INSERT/UPDATE/DELETE `content_block`/`provenance_link`/`lesson_source` khi revision khác DRAFT (service trả 409 `REVISION_LOCKED`); chặn UPDATE nội dung `source_revision`/`source_anchor`; append-only cho các bảng ở §5. Hai role DB: `preclass_migrator` (owner) và `preclass_app` (không UPDATE/DELETE bảng append-only). Test bất biến: APPROVED <=> có `review_event` APPROVE khớp hash hiện tại.
6. **Invalidation (B4–B5).** Sửa X → REVIEW_AGAIN cho mọi block `depends_on` X (bắc cầu) **và** cha trực tiếp của X; chỉ block đang APPROVED chuyển REVIEW_AGAIN, còn lại giữ trạng thái và chạy lại validation. Sinh `block_dependency` cả option→item.
7. **Nguồn mới (B20).** Thêm `PUT /revisions/{id}/sources {sourceRevisionIds}` (chỉ DRAFT): ghép lại anchor theo `excerpt_hash`/locator; không ghép được → link UNRESOLVED. Lesson đã PUBLISHED không bị ảnh hưởng, chỉ có cờ "nguồn đã có bản mới".
8. **Quyền (Q8).** TEACHER chỉ duyệt bài **của mình**; REVIEWER (cờ cấu hình, mặc định tắt) duyệt bài được gán qua bảng `lesson_reviewer`; ADMIN xem audit, không sửa. Tài nguyên của người khác → 404. Progress chỉ cho GV có `class_member.role_in_class=TEACHER` của lớp đó.
9. **Học sinh (B13–B15, C5).** API học sinh trả **DTO danh sách trắng** dựng từ snapshot (không trả dict thô); test snapshot schema HS + test quét key cấm. Một attempt cho mỗi `(assignment, student, item)` (`UNIQUE`); `request_id` chỉ idempotent; bỏ `first_attempt`; `is_correct=null` cho SHORT/rubric; trước `open_at` → 404, sau `due_at` → 409 `ASSIGNMENT_CLOSED` khi nộp.
10. **Generation (D1–D3, D5).** Một worker; khi khởi động `RUNNING → FAILED(restart)`; tối đa 1 job/revision (409); chỉ generate khi revision chưa có block hoặc `mode=append`; không ghi đè block đã sửa/duyệt. Trong prompt LLM dùng alias `A1..An` cho anchors, server ánh xạ. Anchors đặt trong khối dữ liệu có rào; đầu ra chỉ tin qua kiểm tra server, không hứa "chống prompt injection". `AI_ENABLED=false` → generate trả 503 `AI_DISABLED`, phần còn lại vẫn chạy; bảng `usage_daily` đếm token theo `GENERATION_DAILY_TOKEN_BUDGET`.
11. **DOCX và log (D4, D6).** Kiểm magic `PK` + content-types, giới hạn **sau giải nén**, từ chối macro (`vbaProject.bin`, `.docm`). Ghi vào HANDOFF: chưa có malware scan. Bộ lọc redaction `structlog` (Authorization, cookie, giá trị trong lỗi Pydantic) + test log không chứa payload.
12. **Nghiên cứu (D7).** `GET /blocks/{id}/provenance` ghi `audit_log` action `INSPECT_PROVENANCE` (không nội dung).
13. **Cổng review Khải (Q2).** Dừng ngắn, in tóm tắt 3 dòng và chờ phản hồi ở cuối **GĐ3, GĐ6, GĐ8**. Đóng băng tính năng backend **17/11 20:00**; 18/11 chỉ sửa lỗi. Nếu trượt, cắt theo thứ tự: history diff → progress → derivation (rơi về WARNING) → Flashcards → bảng DOCX (rơi về text). **Không cắt**: hash binding, publish gate, PR-08, IDOR.

---

## 0. Bối cảnh và cách làm việc

Bạn là senior backend + AI engineer. Bạn làm **backend** cho PreClass AI. Frontend do người khác (Thiện) làm bằng Next.js và cần **hợp đồng API + data model sớm nhất có thể**. Tech Lead (Khải) đang dự hội nghị, theo dõi và trả lời qua Remote Control trên iPhone; ưu tiên làm tiếp thay vì hỏi.

Quy tắc:

1. Đọc `docs/v2/PreClass_Backend_Plan_v2.md` trước. Đặc tả gốc là file `.docx`; **prompt này thu hẹp phạm vi P0** và thắng khi có mâu thuẫn.
2. Làm theo **giai đoạn ở mục 9**. Hết mỗi giai đoạn: `ruff check`, `mypy --strict`, `pytest` xanh → commit → ghi 2–3 dòng vào `.agents/PROGRESS.md`.
3. **Ưu tiên tuyệt đối: Giai đoạn 1–3 phải xong trước tiên** (khung, data model, OpenAPI hợp đồng + seed). Đó là thứ Thiện cần.
4. Không hỏi lại điều đã quyết. Gặp chỗ chưa rõ: chọn phương án đơn giản nhất phù hợp mục 2, ghi `.agents/DECISIONS_AGENT.md` (vấn đề · lựa chọn · lý do), làm tiếp.
5. **Dừng và để lại ghi chú** trong `.agents/handoffs/T9-backend-v2.md` chỉ khi: cần API key/secret thật; cần đổi một nguyên tắc mục 2; test bảo mật mục 10.1 không thể xanh.
6. Commit nhỏ, tiêu đề tiếng Anh theo style repo. Code + comment tiếng Anh; thông báo lỗi cho người dùng tiếng Việt.
7. Không thêm tính năng ngoài mục 3. Không dùng dịch vụ lưu dữ liệu nước ngoài (Supabase, Firebase, S3 nước ngoài).

---

## 1. Sản phẩm

Web app giúp **giáo viên Địa lí** nhập tài liệu nguồn, cho AI tạo bản nháp học liệu (**Worksheet**, **Flashcards**), **xem từng khối nội dung lấy từ nguồn nào, AI đã biến đổi thế nào**, sửa và duyệt từng khối, rồi mới xuất bản cho học sinh. Học sinh mở bản đã xuất bản, **tự trả lời trước, xem giải thích đã duyệt sau**.

Câu một dòng: *AI tạo bản nháp; hệ thống đối chiếu nguồn; giáo viên chịu trách nhiệm duyệt bản cuối. Truy được nguồn không có nghĩa là đúng — hai trạng thái lưu riêng.*

---

## 2. Nguyên tắc không được phá

| Mã | Nguyên tắc | Thực thi |
|---|---|---|
| PR-01 | Nguồn ≠ đúng | `provenance_link` và `validation_result` / `review_event` là bảng riêng |
| PR-02 | Giáo viên duyệt thực chất | Chỉ TEACHER/REVIEWER duyệt; approval gắn `content_hash` + `source_hashes`; không có endpoint "duyệt tất cả" |
| PR-03 | Evidence first | Block factual phải có anchor hợp lệ, nếu không → FLAGGED (BLOCKER) |
| PR-04 | Editable | Chữ, số liệu, nhãn, đáp án là JSON trong block, không nằm trong ảnh |
| PR-05 | Bản xuất bản bất biến | `published_version.snapshot` không UPDATE (trigger chặn); sửa = revision mới |
| PR-06 | Server xác minh nguồn | **Không tin `anchor_id` do LLM trả về**; kiểm tra tồn tại + thuộc source revision của lesson |
| PR-07 | Số liệu Địa lí | Mọi số trong payload block (trừ số năm, số thứ tự ≤ 10) phải có trong anchor được liên kết; khối `data_fact` bắt buộc `value, unit, period, region` |
| PR-08 | Học sinh không thấy nội bộ | API học sinh không trả provenance, review, validation, `answer_key`, `explanation` trước khi học sinh nộp câu đó |
| PR-09 | AI chỉ chạy khi giáo viên Generate | Không endpoint học sinh nào gọi LLM |
| PR-10 | Chạy được không cần API key | `LLM_PROVIDER=mock` mặc định; mọi test dùng MockProvider |

---

## 3. Phạm vi P0

**Làm:** auth + vai trò; Source Library (dán văn bản, upload DOCX → anchors đoạn và ô bảng); lesson + revision; generate Worksheet/Flashcards (job bất đồng bộ trong process); content blocks + provenance + transformation; validation VAL-01..09; review theo hash + invalidation phụ thuộc; review queue; publish gate + snapshot + withdraw; version history + diff; assignment cho lớp; student view + attempts; audit log; seed 6 bài **mock** Địa lí; OpenAPI + tài liệu cho frontend; Docker Compose; test AT-01..14.

**Không làm:** PDF/PPTX/OCR; Slides, Visual Story, Infographic, Mind map, ảnh AI, audio; reviewer hai bước (để cờ cấu hình, mặc định tắt); chat AI cho học sinh; xuất SCORM/PPTX; đa trường.

---

## 4. Stack

| Lớp | Lựa chọn |
|---|---|
| Ngôn ngữ | Python 3.12, type hint đầy đủ, `mypy --strict` |
| API | **FastAPI**, Pydantic v2 (schema = nguồn sinh OpenAPI) |
| DB | **PostgreSQL 16**, SQLAlchemy 2.0 (async, `asyncpg`), **Alembic** |
| Auth | Cookie session phía server (xem D-001 mục 4); mật khẩu `argon2` |
| DOCX | `python-docx` (đoạn, heading, bảng → anchor theo ô) |
| LLM | Interface `LLMProvider`; `MockProvider` (deterministic, cấu hình được để sinh lỗi cho test) và `OpenAICompatibleProvider` (SDK `openai`, `base_url` cấu hình được — GreenNode/FPT) |
| Job | `asyncio` task + bảng `generation_job` (không cần Redis ở P0) |
| File | Lưu volume local `/data/uploads`, tên file = UUID, kiểm tra mime + kích thước ≤ 10 MB |
| Log | `structlog` JSON; không ghi nội dung nguồn/block vào log |
| Test | `pytest`, `pytest-asyncio`, `httpx.AsyncClient`, `TEST_DATABASE_URL` (Postgres compose) |
| Chất lượng | `ruff`, `mypy`; `gitleaks` ở CI |
| Đóng gói | Docker multi-stage non-root; `infra/compose.*.yml` (api, db, caddy); GitHub Actions CI (job Python) |

Cấu trúc:

```
apps/api/
├── app/
│   ├── main.py  config.py  deps.py  errors.py (RFC 9457)
│   ├── auth/  users/  classes/
│   ├── sources/        # upload, parse, anchors
│   ├── lessons/        # lessons, revisions, lesson_sources
│   ├── blocks/         # content blocks, provenance, transformation, dependencies
│   ├── generation/     # prompt.py, providers/, parser.py, jobs.py
│   ├── validation/     # rules/val_01.py … val_09.py, runner.py
│   ├── review/         # approve/reject/request_changes, invalidation.py, queue
│   ├── publish/        # gate.py, snapshot.py, withdraw, assignments
│   ├── student/        # published view, attempts
│   ├── audit/
│   └── db/             # base.py, session.py, models/
├── alembic/
├── seed/               # seed.py + lessons/*.json (mock)
├── tests/{unit,integration,acceptance}
├── openapi/openapi.json
├── scripts/export_openapi.py  smoke.py
└── pyproject.toml
docs/api/  API_GUIDE.md  DATA_MODEL.md      .agents/  PROGRESS.md  DECISIONS_AGENT.md  handoffs/T9-backend-v2.md
docs/operations/  (RUNBOOK cập nhật)
```

---

## 5. Data model

PK `uuid` (`gen_random_uuid()`), `created_at timestamptz default now()`, enum = `text + CHECK`. Viết `docs/api/DATA_MODEL.md` (bảng, cột, ràng buộc, ví dụ) cho Thiện.

| Bảng | Cột chính | Ràng buộc |
|---|---|---|
| `app_user` | email hoặc `login_code`, `display_name`, `role` TEACHER/REVIEWER/STUDENT/ADMIN, `password_hash` | HS dùng `login_code`, không lưu email/SĐT |
| `class`, `class_member` | `code`, `grade` 10/11; `role_in_class` | `UNIQUE(class_id,user_id)` |
| `source_asset` | `owner_id`, `title`, `license_note`, `visibility` PRIVATE/SCHOOL | |
| `source_revision` | `asset_id`, `version`, `sha256`, `mime`, `file_uri`, `extract_status` PENDING/OK/FAILED, `locked_at` | `UNIQUE(asset_id,version)`; không UPDATE nội dung |
| `source_anchor` | `source_revision_id`, `kind` PARAGRAPH/HEADING/TABLE_CELL/TABLE_ROW, `locator` jsonb (`{para_index}` hoặc `{table, row, col}`), `excerpt`, `excerpt_hash`, `numbers` numeric[] | id ổn định dạng `anc_<revision>_<seq>` lưu ở cột `code` |
| `lesson`, `lesson_revision` | `subject` GEOGRAPHY, `grade`, `title`, `goal`; `revision_no`, `state` DRAFT/IN_REVIEW/PUBLISHED/SUPERSEDED, `base_revision_id`, `version` (optimistic lock) | |
| `lesson_source` | `lesson_revision_id`, `source_revision_id` | |
| `content_block` | `revision_id`, `kind`, `parent_id`, `position`, `payload` jsonb, `content_hash`, `transformation` ORIGINAL/PARAPHRASED/SYNTHESISED/AI_PROPOSED/TEACHER_AUTHORED, `review_status` UNREVIEWED/AUTO_CHECKED/FLAGGED/APPROVED/REVIEW_AGAIN/REJECTED, `no_source_reason`, `is_factual` bool | `content_hash = sha256(canonical_json(payload))` |
| `provenance_link` | `block_id`, `anchor_id`, `relation` derived_from/quotes/supports, `rationale`, `status` VERIFIED/UNRESOLVED | chỉ insert khi anchor thuộc `lesson_source` |
| `block_dependency` | `block_id`, `depends_on_block_id`, `kind` ANSWER_OF/EXPLANATION_OF/FEEDBACK_OF/LABEL_OF | |
| `transformation_event` | `block_id`, `actor_type` AI/TEACHER/SYSTEM, `actor_id`, `operation` GENERATE/EDIT/REGENERATE/SOURCE_REPLACED, `before_hash`, `after_hash`, `generator_version` | append-only |
| `validation_result` | `block_id`, `rule` VAL-01..09, `severity` BLOCKER/WARNING, `outcome` PASS/FAIL, `evidence` jsonb, `method`, `content_hash` | append-only |
| `review_event` | `block_id`, `content_hash`, `source_hashes` text[], `reviewer_id`, `action` APPROVE/REJECT/REQUEST_CHANGES, `note` | append-only; approval hợp lệ chỉ khi hash khớp hiện tại |
| `generation_job` | `revision_id`, `output_type` WORKSHEET/FLASHCARDS, `params`, `status`, `error`, `model`, `prompt_version`, `tokens_in`, `tokens_out` | |
| `published_version` | `lesson_revision_id` UNIQUE, `snapshot` jsonb, `snapshot_hash`, `published_by`, `state` ACTIVE/WITHDRAWN, `withdraw_reason` | trigger chặn UPDATE `snapshot` |
| `assignment` | `published_version_id`, `class_id`, `open_at`, `due_at` | |
| `student_attempt` | `assignment_id`, `student_id`, `item_block_id`, `answer` jsonb, `is_correct`, `request_id` UNIQUE | lần đầu cho mỗi item được giữ (`first_attempt` bool) |
| `audit_log` | `actor_id`, `action`, `resource_type`, `resource_id`, `metadata` (không nội dung) | append-only |

**Kiểu block P0** (`kind` + payload Pydantic, discriminated union):

| kind | payload |
|---|---|
| `heading` | `{text}` |
| `paragraph` | `{text}` |
| `data_fact` | `{label, value: number, unit, period, region, note?}` |
| `instruction` | `{text}` |
| `worksheet_item` | `{stem, item_type: MCQ/SHORT/NUMERIC, skill: READ_TABLE/COMPARE/CALCULATE/EXPLAIN}` |
| `option` | `{label: "A".."D", text}` (con của worksheet_item) |
| `answer_key` | `{correct: "B"}` hoặc `{value, unit, tolerance}` hoặc `{rubric_points: [...]}` |
| `explanation` | `{text}` (phụ thuộc answer_key) |
| `card_front` / `card_back` | `{text}`; card_back có thể kèm `data_fact` |

Dependency tự tạo khi generate: `option`, `answer_key` → con của `worksheet_item`; `explanation` EXPLANATION_OF `answer_key`; `card_back` phụ thuộc `card_front`.

---

## 6. API v1 (hợp đồng cho frontend)

Base `/v1`. JSON camelCase ở API (Pydantic alias), snake_case ở DB. Lỗi RFC 9457 `{type,title,status,detail,code,errors?}` với `code` ổn định. Mọi lệnh sửa nhận `version` (optimistic lock) → `409 VERSION_CONFLICT`. Không có quyền → **404** (chống dò ID). List có `?cursor=&limit=`.

| Method & path | Quyền | Ghi chú |
|---|---|---|
| `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `GET /me` | public / user | |
| `POST /sources` (multipart DOCX hoặc JSON `{title, text}`) | TEACHER | tạo asset + revision 1, parse đồng bộ; trả `extractStatus`, `anchorCount` |
| `POST /sources/{id}/revisions` | owner | tải bản mới → revision mới; các block phụ thuộc → REVIEW_AGAIN |
| `GET /sources`, `GET /sources/{id}` | owner/school | |
| `GET /source-revisions/{id}/anchors` | owner/school | anchors + locator + excerpt |
| `POST /lessons` `{title, grade, goal, sourceRevisionIds[]}` | TEACHER | tạo lesson + revision DRAFT |
| `GET /lessons`, `GET /lessons/{id}`, `GET /lessons/{id}/history` | author | history: revisions, diff tóm tắt, events |
| `POST /lessons/{id}/generate` `{outputType, nItems, focusSkills[]}` | author | 202 `{jobId}` |
| `GET /jobs/{id}` | author | `status`, `error`, `blockCount` |
| `GET /revisions/{id}/blocks` | author/reviewer | cây block + `reviewStatus` + `transformation` + số cảnh báo |
| `POST /revisions/{id}/blocks` | author | thêm block TEACHER_AUTHORED |
| `PATCH /blocks/{id}` `{payload, version}` | author | sửa → transformation_event, hash mới, REVIEW_AGAIN cho block + phụ thuộc, chạy lại validation |
| `DELETE /blocks/{id}` | author | chỉ khi revision chưa publish |
| `GET /blocks/{id}/provenance` | author/reviewer | anchors (excerpt, locator, source revision), transformation, events, validation, reviews |
| `PUT /blocks/{id}/provenance` `{links:[{anchorId, relation, rationale}]}` hoặc `{noSourceReason}` | author | server verify anchor |
| `POST /revisions/{id}/validate` | author | chạy toàn bộ rule, trả tổng hợp |
| `GET /revisions/{id}/review-queue?status=FLAGGED,UNREVIEWED,REVIEW_AGAIN` | reviewer | sắp FLAGGED → REVIEW_AGAIN → UNREVIEWED |
| `POST /blocks/{id}/reviews` `{action, contentHash, note}` | TEACHER/REVIEWER | hash cũ → `409 STALE_REVIEW` |
| `GET /revisions/{id}/publish-check` | author | checklist gate (không ghi) |
| `POST /revisions/{id}/publish` `{confirmChecked:true, version}` | author | gate fail → `409 PUBLISH_BLOCKED` + `blockIds` |
| `POST /revisions/{id}/new-revision` | author | sao chép từ bản đã publish thành DRAFT mới (approval không mang theo) |
| `POST /published/{id}/withdraw` `{reason}` | author | |
| `POST /published/{id}/assignments` `{classId, openAt, dueAt}` | author | |
| `GET /classes`, `GET /classes/{id}/assignments/{aid}/progress` | TEACHER | tỉ lệ đúng lần đầu theo item |
| `GET /student/assignments` | STUDENT | |
| `GET /student/assignments/{id}` | STUDENT lớp đó | snapshot đã lọc (PR-08); withdrawn → `410 WITHDRAWN` |
| `POST /student/assignments/{id}/attempts` `{itemId, answer, requestId}` | STUDENT | trả `isCorrect` + `explanation` (chỉ sau khi nộp) |
| `GET /health` | public | |

Sinh `apps/api/openapi/openapi.json` bằng `apps/api/scripts/export_openapi.py` (CI kiểm tra file không lệch). Viết `docs/api/API_GUIDE.md`: luồng gọi theo màn hình S01–S07, ví dụ request/response thật lấy từ seed, bảng mã lỗi, tài khoản seed, cách chạy mock bằng Prism (`npx @stoplight/prism-cli mock apps/api/openapi/openapi.json`). Bật CORS cho `FRONTEND_ORIGIN`.

---

## 7. Generation pipeline

1. Lấy anchors của mọi `lesson_source`. Đưa vào prompt dạng `[anc_xxx] (TABLE_CELL r2c3, đơn vị: nghìn tấn) 1234,5`.
2. System prompt (tiếng Việt; `PROMPT_VERSION="v1"`, lưu `app/generation/prompt.py`): tạo bản nháp Worksheet/Flashcards Địa lí lớp {grade}, kỹ năng đọc–xử lý–giải thích bảng số liệu; **chỉ dùng thông tin trong anchors**; mỗi block factual phải có `anchorIds`; câu hỏi sư phạm không có nguồn trực tiếp → `transformation=AI_PROPOSED` + `noSourceReason`; trích nguyên văn → `ORIGINAL`; trả **chỉ JSON** theo schema.
3. Gọi provider: JSON schema/structured output, temperature 0.3, timeout 60 s, retry 1 lần khi JSON lỗi.
4. Parse Pydantic. Với từng block: lọc `anchorIds` không hợp lệ (ghi VALIDATION VAL-01 FAIL), tạo link VERIFIED cho id hợp lệ, `review_status = UNREVIEWED`, chạy validation → AUTO_CHECKED hoặc FLAGGED.
5. Không bao giờ tự đặt APPROVED. Ghi `generation_job` (model, prompt_version, token).
6. `MockProvider`: sinh block từ anchors của seed theo luật đơn giản; có cờ `MOCK_INJECT=fake_anchor,changed_quote,new_number,two_keys` để test sinh lỗi.

## 8. Validation và invalidation

| Rule | Phát hiện | Severity |
|---|---|---|
| VAL-01 | anchor không tồn tại / không thuộc source revision của lesson | BLOCKER |
| VAL-02 | block ORIGINAL không khớp nguyên văn anchor (chuẩn hóa Unicode NFC, khoảng trắng; **giữ dấu tiếng Việt**) — trả vị trí khác | BLOCKER |
| VAL-03 | block `is_factual` không có link VERIFIED và không có `noSourceReason` hợp lệ; hoặc số trong payload ∉ `numbers` của anchors liên kết (PR-07) | BLOCKER |
| VAL-04 | worksheet_item MCQ có ≠ 1 đáp án đúng, `answer_key` trỏ option không tồn tại, NUMERIC thiếu unit | BLOCKER |
| VAL-05 | đánh số/label option trùng hoặc thiếu (A–D) | WARNING (BLOCKER nếu thiếu option đúng) |
| VAL-06 | block có approval nhưng hash hoặc source hash đã đổi | BLOCKER |
| VAL-07 | (P1, ảnh) — để stub trả PASS | — |
| VAL-08 | thuật ngữ nghi vấn theo danh sách `seed/glossary_geo.txt` | WARNING |
| VAL-09 | source asset thiếu `license_note` khi visibility SCHOOL | BLOCKER |

Invalidation (`review/invalidation.py`, một transaction): sửa block → block + mọi block phụ thuộc theo `block_dependency` chuyển REVIEW_AGAIN; thay source revision → mọi block có link tới anchor của revision cũ → REVIEW_AGAIN và link đánh dấu UNRESOLVED cho tới khi tác giả gán lại.

Publish gate (server): mọi block thuộc revision ở APPROVED với hash hiện tại; không validation BLOCKER FAIL ở hash hiện tại; `confirmChecked=true`; `version` khớp. Snapshot = cây block đã chuẩn hóa + `snapshot_hash`.

---

## 9. Giai đoạn và cổng kiểm tra

| GĐ | Nội dung | Cổng |
|---|---|---|
| **1** | Khung repo, pyproject, Docker Compose dev (Postgres + api), config, errors RFC 9457, `/health`, CI | `pytest` + `ruff` + `mypy` xanh; CI chạy |
| **2** | Models + Alembic migration (kèm trigger append-only và chặn sửa snapshot), `DATA_MODEL.md`, seed (2 bài trước, đủ 6 bài sau): 1 lớp 10A1 + 1 lớp 11A1, 1 GV `gv.dia@preclass.local`, 30 HS `HS10-01..15`, `HS11-01..15`, admin; **6 bài mock** (3 lớp 10, 3 lớp 11) mỗi bài 1 source text + 1 bảng số liệu **giả, ghi rõ "DỮ LIỆU MINH HỌA"** | Migration up/down sạch; test trigger |
| **3** | Pydantic schema + route khai báo + `examples` cho mọi endpoint mục 6 (và `PUT /revisions/{id}/sources`); `openapi.json`; `API_GUIDE.md`; **v0 14/11, freeze v1 16/11 sáng** | Prism mock chạy đúng schema; snapshot test OpenAPI; **cổng review Khải** |
| 4 | Auth thật + phân quyền + test IDOR | Test 10.1 xanh |
| 5 | Sources: text + DOCX parse → anchors; source revision mới | Test parse đoạn + bảng; hash đổi khi upload bản mới |
| 6 | Lessons, blocks, provenance, PATCH + transformation + invalidation | AT-03, AT-04, AT-08, AT-09 |
| 7 | Generation (Mock + OpenAICompatible) + validation VAL-01..09 | AT-01, AT-02, AT-05, AT-06 |
| 8 | Review, queue, publish gate, snapshot, withdraw, new-revision, history | AT-10, AT-11, AT-12, AT-14 |
| 9 | Student API + attempts + progress | AT-13 + test PR-08 |
| 10 | Docker staging/prod (api + web + db + caddy + backup `pg_dump`), `RUNBOOK.md`, HANDOFF | `docker compose up` máy sạch chạy seed + toàn luồng bằng script `scripts/smoke.py` |

Sau GĐ 3, chạy `apps/api/scripts/export_openapi.py`, commit `apps/api/openapi/openapi.json`, ghi rõ trong `.agents/PROGRESS.md`: "Hợp đồng API v0 sẵn sàng cho frontend". Các GĐ sau **chỉ thêm field, không đổi tên/xóa field** nếu không ghi vào `.agents/DECISIONS_AGENT.md`.

---

## 10. Test bắt buộc

### 10.1 Quyền và bảo mật
- GV A truy cập source/lesson/block của GV B → 404.
- STUDENT gọi mọi route giáo viên → 403/404; STUDENT lớp khác mở assignment → 404.
- Response học sinh **không chứa** các key: `provenance`, `anchor`, `review`, `validation`, `answerKey`, `explanation` (trước attempt) — test quét JSON đệ quy.
- Body chứa `role`, `ownerId`, `reviewerId` bị bỏ qua.
- Upload file không phải DOCX hoặc > 10 MB → 422; tên file không dùng làm đường dẫn.

### 10.2 Acceptance AT-01..14 (từ đặc tả team, áp dụng P0)
AT-01 đổi một dấu tiếng Việt trong trích ORIGINAL → VAL-02 BLOCKER, trả vị trí khác · AT-02 LLM trả anchor không tồn tại → link bị loại, block FLAGGED · AT-03 đổi answer_key sau APPROVED → key + explanation REVIEW_AGAIN · AT-04 block tổng hợp 3 anchors → provenance trả đủ 3 · AT-05 câu hỏi AI_PROPOSED không nguồn → cần `noSourceReason`, vẫn phải duyệt · AT-06 AI thêm số mới không có trong nguồn → VAL-03 BLOCKER · AT-07 (P1 ảnh) bỏ qua, ghi skip · AT-08 upload source mới cùng tên → revision/hash mới, block phụ thuộc REVIEW_AGAIN · AT-09 sửa block đã duyệt → approval mất hiệu lực · AT-10 publish khi còn BLOCKER → 409, không tạo snapshot · AT-11 sửa sau publish → revision mới, snapshot cũ nguyên · AT-12 withdraw → học sinh nhận 410 + lý do được log · AT-13 học sinh mở provenance → 404 · AT-14 duyệt với hash cũ → 409 STALE_REVIEW.

---

## 11. Biến môi trường (`.env.example`)

```
DATABASE_URL=postgresql+asyncpg://preclass:preclass@localhost:5432/preclass
TEST_DATABASE_URL=postgresql+asyncpg://preclass:preclass@localhost:5432/preclass_test
SESSION_SECRET=replace-with-a-local-random-value
AI_ENABLED=true
FRONTEND_ORIGIN=http://localhost:3000   # chỉ dùng khi dev tách origin
UPLOAD_DIR=./data/uploads
LLM_PROVIDER=mock            # mock | openai_compatible
LLM_BASE_URL=
LLM_API_KEY=
LLM_MODEL=
MOCK_INJECT=
GENERATION_DAILY_TOKEN_BUDGET=300000
```

## 12. Định nghĩa "Xong" cho phiên này

- [ ] GĐ 1–3 xong và commit: Thiện có `apps/api/openapi/openapi.json`, `docs/api/API_GUIDE.md`, `docs/api/DATA_MODEL.md`, tài khoản seed, lệnh chạy 1 dòng.
- [ ] Đi xa nhất có thể qua GĐ 4–10, mỗi GĐ có cổng xanh.
- [ ] `.agents/handoffs/T9-backend-v2.md` cho Khải: đã xong gì, còn gì, test nào chưa xanh, quyết định trong `DECISIONS_AGENT.md`, việc cần làm tiếp (điền LLM key, chọn model, nội dung 6 bài thật từ giáo viên).
- [ ] Không có secret hoặc dữ liệu thật trong repo.

Bắt đầu từ Giai đoạn 1. Sau mỗi giai đoạn in tóm tắt 3 dòng.
