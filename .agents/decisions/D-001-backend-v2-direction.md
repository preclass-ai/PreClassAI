# Decision: D-001 — Hướng backend v2 (Source-to-Output Traceability)

Status: `accepted` (Khải xác nhận "OK" toàn bộ Q1–Q9, 2026-11-14)
Owner: Khải (Tech/Dev Lead) · soạn: Claude Code (bước đánh giá, chưa viết code)
Date: 2026-11-14
Revisit: sau cổng GĐ3 (hợp đồng API v0) và sau 18/11 (kiểm thử FE)

Phạm vi đã đọc: `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `README.md`, `SECURITY.md`, `.agents/` (README, T7/T8/T9, handoffs, templates, tên skills), `docs/01–07`, `docs/adr|api|operations|security|ui|research|tooling`, `apps/web/**` (toàn README), `content/`, `drizzle/`, `infra/*`, `scripts/`, `.github/*`, `.env.example`, `.claude/settings.json`, `docs/v2/*` (đặc tả `.docx` đã trích bằng `python-docx` qua `uv run`). Đã chạy kiểm tra môi trường (git, docker, uv, ports). Không sửa file nào khác.

---

## 1. Tóm tắt (5 dòng)

1. **Repo chưa có dòng code ứng dụng nào** (không `package.json`, không `apps/api`, `apps/web` chỉ là README đánh dấu). Phần chạy được duy nhất: CI policy, Compose/Caddy, `backup.sh`/`restore.sh`. Tức là chọn FastAPI hay Next.js **không tốn chi phí chuyển đổi code**, chỉ tốn chi phí sửa tài liệu.
2. **Thiết kế cũ (H.A.B.I.T, Ngữ văn, học sinh tự học + AI tutor) và v2 (Địa lí, giáo viên duyệt nguồn, học sinh chỉ làm bài đã xuất bản) là hai sản phẩm khác nhau.** Docs 01, 02, 05, 06 và 3 file `docs/security/*` đã lỗi thời; giữ phần hạ tầng/vận hành/quy tắc an toàn, đánh dấu superseded phần còn lại.
3. **Prompt v2 mạnh về nguyên tắc và test, yếu ở 4 chỗ**: (a) PR-07 mâu thuẫn với câu hỏi CALCULATE, (b) hash binding/bất biến chưa kín (chỉ chặn sửa `snapshot`, còn block sau publish, hash không phủ `kind/parent`, TOCTOU khi duyệt), (c) đường dẫn/ADR/`.env` còn mâu thuẫn với repo, (d) 10 giai đoạn trong ~4 ngày là quá sức.
4. **Lịch đã trễ ~1 ngày**: kế hoạch ghi "13/11 chạy prompt"; hôm nay 14/11 (H1) chưa có `apps/api`. Đề xuất: H1 = hợp đồng **v0** tối 14/11, **freeze v1** sáng 16/11; làm theo lát cắt dọc Worksheet trước.
5. **Khuyến nghị giữ FastAPI** (Q1) vì greenfield cả hai phía, DOCX/Unicode/Decimal thuận Python, OpenAPI sinh từ Pydantic là hợp đồng cho Thiện; điều kiện: Khải đủ thoải mái review Python, và dùng Caddy để FE/API cùng origin.

---

## 2. Hiện trạng repo — "đã có thật" vs "chỉ là tài liệu/khung"

### 2.1 Có thật (chạy/kiểm được)

| Thành phần | Trạng thái |
|---|---|
| `.github/workflows/ci.yml` | Job `repository-policy` chạy; job `app` (pnpm) tắt bằng `APP_CI_ENABLED` |
| `infra/compose.{dev,staging,prod}.yml`, `Caddyfile` | Có thật nhưng chỉ cho kiến trúc cũ (`web:3000`); dev chỉ có Postgres 16 |
| `infra/backup.sh`, `restore.sh` | Dùng được cho FastAPI (pg_dump + age); cần CRLF→LF (xem mục 5) |
| `.agents/` protocol, template, 14 skills copy (cloudflare, figma*, playwright, security-*, gh-*) | Có thật; skills thiên về Next.js/TS |
| Git: nhánh `main`, 5 commit, 3 nhánh dependabot (checkout/setup-node/pnpm action) trên remote | Chưa commit (untracked): `.agents/tasks/T9-backend-v2.md`, `.claude/`, `docs/v2/` |

### 2.2 Chỉ là tài liệu / khung rỗng

`apps/web/**` (15 README, 0 mã), `content/`, `drizzle/`, `scripts/`, `docs/api|adr|ui|research` (mỗi cái 1 README), `.env.example` (biến cũ), ADR-0001..0009 (nằm trong `docs/01`, trạng thái **Proposed**, chưa có file riêng trong `docs/adr/`).

### 2.3 Bảng giữ / sửa / bỏ

| Hạng mục | Quyết định | Ghi chú |
|---|---|---|
| `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `.agents/README.md`, templates, `SECURITY.md` | **Giữ** | Chỉ sửa mục "Project Structure" và "Build, Test" của `AGENTS.md` cho `apps/api/` (đã nằm trong prompt) |
| Nguyên tắc `docs/07` (không dữ liệu HS thật, AI tắt được toàn cục, credential do Mentor/trường giữ, ADR cho đổi schema/auth/AI/host) | **Giữ** | Là ràng buộc cứng; prompt v2 phải mang `AI_ENABLED` kill switch (hiện thiếu) |
| `docs/security/incident-response.md`, `docs/operations/backup-restore-runbook.md`, `monitoring-runbook.md` | **Giữ** | Đổi `/api/health` → `/v1/health` |
| `docs/operations/deployment-runbook.md` | **Sửa** | `/api/health`, `/api/ready` → `/v1/*`; 2 image (api, web); file `infra/.env.*.example` mà runbook nhắc **chưa tồn tại** |
| `docs/security/threat-model.md`, `data-inventory.md`, `access-control-matrix.md` | **Sửa (viết lại tài sản)** | Hiện nói về phiên học H.A.B.I.T/chat turn/ghi chú riêng. v2: source DOCX (bản quyền), block/answer key, snapshot, attempt; LLM chỉ nhận anchors, **không bao giờ** dữ liệu HS |
| `infra/compose.dev.yml` | **Sửa** | Thêm `api`; giữ Postgres, thêm test DB |
| `infra/compose.staging.yml`, `compose.prod.yml` | **Sửa** | `web` đơn → `api` + `web`; staging thiếu healthcheck Postgres nhưng `web depends_on: service_healthy` (cần thử `up`, chưa xác minh được vì thiếu `.env.staging`); `api` cần ra internet để gọi LLM nên phải ở network `edge` |
| `infra/Caddyfile` | **Sửa** | Route `/v1/*` → `api:8000`, còn lại → `web:3000` (cùng origin). Giữ header bảo mật |
| `.github/workflows/ci.yml` | **Sửa (thêm)** | Job Python (`setup-uv`, ruff, mypy, pytest, export-openapi diff, gitleaks); job `app` pnpm vẫn tắt đến khi Thiện có lockfile |
| `.github/CODEOWNERS`, `dependabot.yml` | **Sửa** | Thêm `/apps/api/`, `/apps/api/alembic/` cho leads; dependabot `uv`/`pip` cho `apps/api` |
| `.env.example` | **Sửa** | Có 2 `DATABASE_URL` khác dạng nếu "thêm" mục 11; xem C-05 |
| `.gitignore` | **Sửa (thêm)** | Đã nêu trong prompt; thêm `*.age`, `apps/api/data/` |
| `docs/03-budget-estimate.md` | **Sửa sau** | Tính lại chi phí LLM: chỉ khi GV bấm Generate, không còn chat HS. Không chặn GĐ 1–3 |
| `docs/04-infrastructure-source-code.md` (phần host, domain, VPS) | **Giữ** | §6b "tái sử dụng prototype" vẫn đúng |
| `docs/01`, `docs/02` (Next monolith, H.A.B.I.T ERD, AI tutor pipeline, endpoint v0), `docs/05` (RACI Ngữ văn), `docs/06` (master plan G0–G6) | **Bỏ khỏi hiệu lực** | Thêm banner "Superseded by D-001/ADR-0010", **không xóa**, **không viết lại** (ADR README cấm sửa ADR đã accepted; cần ADR kế thừa) |
| `drizzle/`, `apps/web/src/{learning,ai,teacher,db}` README | **Bỏ khỏi hiệu lực** | Alembic nằm trong `apps/api/alembic/`. `apps/web` là việc của Thiện: để Thiện quyết, backend không đụng |
| `content/` (gói bài Ngữ văn L1–L4) | **Giữ chỗ** | Seed mock đặt ở `apps/api/seed/`; `content/lessons` dùng cho bài thật sau (cùng JSON schema) |
| `.claude/settings.json` | **Sửa** | Xem mục 5.2 |

---

## 3. Nhận xét prompt v2 (`docs/v2/CLAUDE_CODE_PROMPT_Backend_v2.md`)

### 3.1 Điểm tốt

- §2: bảng PR-01..PR-10 có cột **Thực thi** cụ thể (không chỉ khẩu hiệu); PR-06 "không tin `anchor_id` của LLM" và PR-10 "chạy được không cần key" đúng hướng.
- §6: lỗi RFC 9457 với `code` ổn định, **404 chống dò ID**, optimistic lock `version` → 409, camelCase ở API/snake_case ở DB: hợp đồng đủ rõ để Thiện sinh client.
- §7: `MOCK_INJECT=fake_anchor,changed_quote,new_number,two_keys` biến AT-01/02/06 thành test tất định. Rất hay.
- §8: invalidation trong **một transaction**; publish gate kiểm ở server.
- §9: ưu tiên GĐ1–3 cho Thiện; "chỉ thêm field, không đổi tên/xóa" sau GĐ3.
- §10.1: test IDOR, quét JSON đệ quy cho HS, body có `role/ownerId` bị bỏ qua.
- Đầu prompt "Điều chỉnh theo repo" (thắng khi mâu thuẫn), commit style, không push, không đụng `apps/web/`.

### 3.2 Điểm yếu và đề xuất sửa

**A. Mâu thuẫn nội bộ / với repo**

| # | Vị trí | Vấn đề | Sửa |
|---|---|---|---|
| A1 | §0 quy tắc 1, 2, 5; §4 cây thư mục (`backend/`, `docs/...`, `openapi/`); §6 đoạn cuối; §9 "Sau GĐ 3"; §12 | Còn đường dẫn cũ (`docs/PreClass_Backend_Plan_v2.md`, `backend/`, `docs/PROGRESS.md`, `docs/HANDOFF.md`) dù khối "Điều chỉnh" đã đổi. Agent dễ tạo sai chỗ | Thay trực tiếp trong thân prompt, đừng dựa vào "override" |
| A2 | Khối "Điều chỉnh" dòng ADR | `ADR-0001` **đã dùng** cho "Next.js monolith" (docs/01). Và agent tự viết ADR ở GĐ1 trái `AGENTS.md`/`.agents/README.md` ("dừng và viết ADR **trước** khi triển khai") | ADR-**0010**, do D-001 đã duyệt cấp phép; agent chỉ chuyển nội dung D-001 thành ADR, không tự quyết |
| A3 | §4 "Đóng gói: `docker-compose.yml`" vs "Điều chỉnh: không tạo file compose mới ở gốc" | Hai chỉ dẫn ngược nhau | Xóa `docker-compose.yml`; ghi `infra/compose.*.yml` |
| A4 | §11 vs `.env.example` hiện có | `DATABASE_URL` (2 dạng), `LLM_BASE_URL`, `LLM_API_KEY` trùng khóa; `SESSION_SECRET`, `AI_ENABLED`, `AI_DAILY_BUDGET_VND`, `BACKUP_ENCRYPTION_KEY` bị bỏ qua | Một danh sách hợp nhất: giữ `AI_ENABLED` (kill switch, bắt buộc theo docs/07), đổi `GENERATION_DAILY_TOKEN_BUDGET` thay `AI_DAILY_BUDGET_VND` có ghi chú |
| A5 | §0.2 "`ruff`, `mypy --strict`, `pytest` xanh → commit" nhưng quy tắc 6 | Chỉ nói Conventional Commits; repo dùng "tiêu đề ngắn, mệnh lệnh" (AGENTS.md); phần Điều chỉnh đã nói. Chọn một | Giữ style repo, bỏ "Conventional Commits" |
| A6 | Đầu ra cuối mỗi GĐ phải kèm trailer commit theo hệ thống (Co-Authored-By) | Prompt không nhắc | Thêm một dòng; thuộc về harness, không phải prompt. Bỏ qua nếu Khải không cần |

**B. Data model và bất biến (PR-02, PR-05, PR-06)**

| # | Vị trí | Lỗ hổng | Đề xuất |
|---|---|---|---|
| B1 | §5 `content_block.content_hash = sha256(canonical_json(payload))` | Hash chỉ phủ `payload`. Đổi `kind`, `parent_id`, `position` (đổi vị trí/đổi cha của `option`, `answer_key`) **không** làm mất duyệt. Duyệt `worksheet_item` không ràng buộc tập `option` con | Hash = `sha256(canonical_json({kind, payload, parent_hash_or_id, transformation, noSourceReason}))`; thứ tự/cha của con nằm trong hash của cha qua `children_hash` hoặc sửa con ⇒ invalidate cha (xem B4) |
| B2 | §5 `review_event.source_hashes text[]` | Không định nghĩa "source hash" là gì | `source_hashes` = danh sách `sha256` của **`source_revision`** (sort, unique) của mọi link `VERIFIED` + `excerpt_hash` của từng anchor. Approval hợp lệ khi cả hai khớp hiện tại (VAL-06) |
| B3 | §5 `content_block` | Thiếu cột `version` cho `PATCH /blocks/{id} {payload, version}` (§6) | Thêm `version int`, tăng mỗi lần PATCH |
| B4 | §8 Invalidation + §5 `block_dependency` | Hướng phụ thuộc mơ hồ ("`option`, `answer_key` → con của `worksheet_item`" là parent, nhưng `block_dependency.kind` dùng ANSWER_OF/…). Sửa `option` có kéo theo `worksheet_item` và `answer_key` không? | Chốt quy tắc: sửa X ⇒ REVIEW_AGAIN cho mọi block **depends_on X** (bắc cầu) **và** cha trực tiếp của X. Sinh `block_dependency` cho cả option→item. Test AT-03 mở rộng |
| B5 | §8 "chuyển REVIEW_AGAIN" | Block chưa từng APPROVED cũng bị REVIEW_AGAIN? Sơ đồ trạng thái (Plan §6) chỉ cho APPROVED→REVIEW_AGAIN | Chỉ APPROVED → REVIEW_AGAIN; còn lại giữ trạng thái và chạy lại validation |
| B6 | §5 `review_status` (cột) và `review_event` (append-only) | Hai nguồn sự thật có thể lệch | Một nơi duy nhất cập nhật `review_status`, trong transaction cùng `review_event`; test bất biến "APPROVED ⇔ có review_event APPROVE khớp hash hiện tại" chạy trên toàn seed |
| B7 | §6 `POST /blocks/{id}/reviews` kiểm hash | TOCTOU: PATCH chen giữa kiểm và ghi | `SELECT … FOR UPDATE` block, kiểm `content_hash` và `version` trong cùng transaction; test song song (hai task) |
| B8 | §6 publish | Tương tự: gate đọc, rồi snapshot, giữa chừng có PATCH | Khóa `lesson_revision` (`FOR UPDATE`) + so `version`; dựng snapshot **từ cùng transaction** |
| B9 | PR-05: "trigger chặn UPDATE `published_version.snapshot`" | Chỉ bảo vệ snapshot. Sau publish, `content_block` của revision đó **vẫn sửa được** (revision `PUBLISHED` mà PATCH không bị chặn), làm lệch history/diff với snapshot | Trigger trên `content_block`, `provenance_link`, `lesson_source`: chặn INSERT/UPDATE/DELETE nếu `lesson_revision.state <> 'DRAFT'`; service cũng kiểm (trả 409 `REVISION_LOCKED`) |
| B10 | §5 `source_revision` "không UPDATE nội dung", `source_anchor` | Chỉ là lời, không trigger | Trigger chặn UPDATE các cột nội dung của `source_revision`, `source_anchor` (chỉ cho `extract_status`, `locked_at` đổi một lần) |
| B11 | §5 bảng append-only | Trigger là lớp 1; ADR-0002 cũ yêu cầu **role DB app không có UPDATE/DELETE** | Hai role: `preclass_migrator` (owner) và `preclass_app` (GRANT SELECT/INSERT; UPDATE chỉ trên bảng cần). Là điều kiện kiểm được trong test |
| B12 | §6 `DELETE /blocks/{id}` với `review_event`/`validation_result` append-only FK | Xóa vật lý mâu thuẫn append-only (CASCADE là xóa lịch sử) | Soft delete: `deleted_at`, loại khỏi cây và gate, giữ sự kiện |
| B13 | §5 `student_attempt` "`request_id UNIQUE`; lần đầu giữ (`first_attempt`)" | Không rõ HS được thử lại không. Nếu thử lại được, HS thử sai để mở `explanation` rồi làm lại | Chốt P0: **một attempt mỗi (assignment, student, item)**, `UNIQUE(assignment_id, student_id, item_block_id)`; `request_id` chỉ để idempotent retry cùng nội dung. Bỏ `first_attempt` |
| B14 | §5 `answer_key` có `rubric_points` và item `SHORT` | `is_correct` cho SHORT/rubric không xác định | `is_correct = null` cho SHORT/rubric; progress chỉ tính MCQ/NUMERIC; hoặc so khớp chuẩn hóa nếu có `accepted[]` |
| B15 | §5 `assignment.open_at/due_at` | Không nói server có chặn truy cập/nộp ngoài khoảng | Chặn: trước `open_at` → 404; sau `due_at` vẫn xem, nộp → 409 `ASSIGNMENT_CLOSED` (hoặc cho nộp trễ có cờ) |
| B16 | §5 `source_anchor.numbers numeric[]` + PR-07 | Số tiếng Việt: `1.234,5` vs `1,234.5`, `1.234` là 1234 hay 1,234? Parser sai ⇒ VAL-03 sai hàng loạt | Một parser chuẩn (dấu `.` nghìn, `,` thập phân theo VN) cho cả anchors lẫn payload, so bằng `Decimal`; số mơ hồ (`1.234`) chấp nhận cả hai cách đọc; test bảng riêng |
| B17 | §2 PR-07 "mọi số ∉ anchor ⇒ lỗi" vs §5 `worksheet_item.skill = CALCULATE` | **Mâu thuẫn**: đáp án của câu tính (tổng, tỉ lệ, chênh lệch) không nằm trong anchors, nên mọi CALCULATE bị VAL-03 BLOCKER | Xem Q5 |
| B18 | §6 anchor id `anc_<revision>_<seq>` với `<revision>` là UUID | ID dài, LLM dễ chép sai; tốn token | Trong prompt LLM dùng alias ngắn `A1..An`; server ánh xạ alias → anchor (PR-06 vẫn đủ: chỉ alias trong bảng này hợp lệ) |
| B19 | §5 thiếu `refresh_token` | Prompt chọn "refresh xoay vòng" nhưng không có bảng, không phát hiện tái sử dụng | Xem Q6 |
| B20 | §6 `POST /sources/{id}/revisions` | Làm gì với lesson đang dùng revision cũ? "các block phụ thuộc → REVIEW_AGAIN" nhưng `lesson_source` vẫn trỏ revision cũ (bất biến) và không có endpoint đổi nguồn | Thêm `PUT /revisions/{id}/sources {sourceRevisionIds}` (chỉ DRAFT) và thuật toán ghép lại anchor theo `excerpt_hash`/locator; link không ghép được → UNRESOLVED. Lesson đã PUBLISHED không bị ảnh hưởng, chỉ hiện cảnh báo "nguồn đã có bản mới" |

**C. Quyền và IDOR**

| # | Vị trí | Vấn đề | Đề xuất |
|---|---|---|---|
| C1 | §2 PR-02 "chỉ TEACHER/REVIEWER duyệt" | Đọc theo chữ: **mọi** TEACHER duyệt bài của GV khác | Xem Q8 |
| C2 | §10.1 "STUDENT gọi route GV → 403/404" | Hai mã khiến FE phải xử lý cả hai | Quy ước: sai **vai trò** → 403 `FORBIDDEN_ROLE`; sai **sở hữu/lớp** → 404. Ghi vào API_GUIDE |
| C3 | §5 `source_asset.visibility SCHOOL` | GV khác đọc nguồn SCHOOL; ai chuyển PRIVATE→SCHOOL, VAL-09 yêu cầu `license_note`. Nguồn SCHOOL dùng trong lesson của GV khác, sau đó chủ thu hồi? | Snapshot đã copy nên không ảnh hưởng; lesson DRAFT mất quyền ⇒ link UNRESOLVED; ghi rõ |
| C4 | §6 `/classes/{id}/assignments/{aid}/progress` | "TEACHER": GV nào? | Chỉ GV có `class_member.role_in_class = TEACHER` của lớp đó (có test IDOR) |
| C5 | §10.1 PR-08 test "quét key cấm" | Danh sách đen: thêm trường mới là lọt | **Danh sách trắng**: HS API dùng DTO riêng dựng từ snapshot, không trả `dict` thô; test snapshot "schema HS" + test quét |

**D. Pipeline, job, vận hành**

| # | Vị trí | Vấn đề | Đề xuất |
|---|---|---|---|
| D1 | §4 Job `asyncio` + `generation_job` | Mất job khi restart; nhiều worker chạy trùng | Một worker uvicorn ở P0; khi khởi động chuyển `RUNNING → FAILED(restart)`; tối đa 1 job đang chạy/revision (409) |
| D2 | §6 generate | Revision đã có block thì ghi đè, nối thêm, hay lỗi? | P0: chỉ cho generate khi revision **chưa có block** hoặc `mode=append`; không ghi đè block đã sửa/duyệt |
| D3 | §11 `GENERATION_DAILY_TOKEN_BUDGET` | Không có bảng/cơ chế đếm, không có kill switch | Bảng `usage_daily(date, tokens_in, tokens_out)`; `AI_ENABLED=false` ⇒ generate trả 503 `AI_DISABLED`, mọi thứ còn lại chạy được (docs/07) |
| D4 | §4 "python-docx", mime ≤ 10 MB | Zip bomb, `.docm`, tên file | Kiểm magic `PK`, content-types, giới hạn **sau giải nén** (ví dụ 50 MB, 50 000 phần tử), từ chối `vbaProject.bin`; đặc tả §10 yêu cầu malware scan: P0 ghi nhận "chưa làm", không giả vờ |
| D5 | §7 prompt injection qua DOCX | Không nhắc. Nguồn là tài liệu không tin cậy | Prompt hệ thống đặt anchors trong khối dữ liệu có rào; **đầu ra chỉ được tin qua kiểm tra server** (PR-06/VAL). Nêu rõ trong DECISIONS; không hứa "chống inject" |
| D6 | §4 Log | "không ghi nội dung nguồn/block" tốt; chưa có redaction của `Authorization`, cookie, `detail` lỗi Pydantic chứa giá trị | Thêm bộ lọc `structlog`, test log không chứa payload |
| D7 | Đặc tả §13 (đo hành vi duyệt) | Prompt không ghi lại việc mở Source Inspector | Ghi `audit_log(action=INSPECT_PROVENANCE)` khi `GET /blocks/{id}/provenance` (không nội dung). Rẻ, và cần xin phép đạo đức cho nghiên cứu (đặc tả §13) |

**E. Thiếu / thừa so với đặc tả `.docx`**

- **Đã cắt khỏi P0 của đặc tả (đặc tả: 4 đầu ra, Slides + Visual Story; input DOCX/PPTX/PDF):** Slides, Visual Story, PPTX/PDF/OCR, kiểu block `image`, `callout`, `slide`, `story_scene`, VAL-07 thật. `PreClass_Backend_Plan_v2.md` §0 đã chốt việc này, nhưng **chưa có xác nhận của Product** (chị Hiển/anh Khang) rằng giám khảo/đặc tả chấp nhận 2/4 đầu ra. Cần ghi vào ADR-0010.
- **Đặc tả có mà prompt thiếu:** malware scan (D4), retention/xóa dữ liệu HS (đặc tả §10), chỉ số quan sát (§10: số import lỗi, anchor unresolved, tỉ lệ bị chặn), autosave (có thể đạt bằng `version` + 409), role Reviewer hai bước (có cờ), S06 diff (prompt có `history` nhưng "diff tóm tắt" chưa định nghĩa).
- **Thừa so với P0 trong 4 ngày (đề xuất hoãn):** `OpenAICompatibleProvider` thật (chỉ khi có key và còn thời gian; kiến trúc `LLMProvider` giữ), diff chi tiết ở history, `/progress`, VAL-08 glossary (WARNING), VAL-09 thực chất (chỉ cờ), pagination cursor cho list nhỏ, Testcontainers (xem mục 5), pre-commit/gitleaks cục bộ (để CI), refresh xoay vòng (xem Q6), 6 bài mock (2 bài đủ cho AT; 6 bài trước 17/11), Flashcards (làm sau Worksheet qua cùng engine).

### 3.3 Rủi ro tiến độ

| Rủi ro | Dấu hiệu | Giảm thiểu |
|---|---|---|
| H1 (14/11) trượt: hôm nay chưa có `apps/api` | Khải vắng, agent chạy một mình | Hợp đồng **v0 draft** tối 14/11 (OpenAPI + ví dụ + Prism), freeze v1 **sáng 16/11** sau khi Thiện review; sau freeze chỉ thêm field |
| Thiện chặn nếu chờ route thật | `apps/web` chưa có mã/lockfile; client chưa sinh | Thiện dùng Prism + `openapi-typescript` ngay từ v0; backend thật lên local qua `docker compose up` từ 15/11, không phụ thuộc staging |
| Staging cho 16–17/11 chưa có chủ | docs/04 vẫn "Desktop + Cloudflare Tunnel" pilot; chưa rõ máy | Fallback: Thiện chạy compose local; staging là bonus, không là cổng |
| 10 GĐ/4 ngày với agent tự chạy | GĐ6–8 là lõi nghiệp vụ, mỗi GĐ ≥ 1/2 ngày | Lát cắt dọc (Q3); Khải review ở cuối GĐ3, GĐ6, GĐ8 |
| Review chất lượng: Khải vắng, agent tự duyệt | Remote Control iPhone, prompt quyền | `acceptEdits` + allowlist (mục 5.2); cổng review bằng chat 3 dòng/GĐ |
| AT-01..14 đều cần dữ liệu seed tốt | Seed mock sai ⇒ test sai | 2 bài seed hoàn chỉnh trước GĐ6; bảng số đã gắn dấu "DỮ LIỆU MINH HỌA" |
| Hash/bất biến làm trễ nếu bổ sung muộn | B1–B11 | Đưa vào GĐ2 (migration) ngay, rẻ hơn sửa sau |
| Kiểm thử FE 18/11 sát nước rút, backend chỉ "trực" | | Đóng băng tính năng backend **17/11 20:00**; 18/11 chỉ sửa lỗi |

### 3.4 FastAPI hay quay về Next.js Route Handlers + Drizzle?

| Tiêu chí | FastAPI (v2) | Next.js Route Handlers + Drizzle (docs cũ) |
|---|---|---|
| Chi phí chuyển đổi | Không (chưa có mã). Phải ghi ADR và đánh banner docs 01/02 | Không (chưa có mã). Docs 02/07, CI pnpm, Compose, CODEOWNERS đã viết sẵn cho nó |
| Hợp đồng cho Thiện | OpenAPI **sinh từ Pydantic**, `openapi-typescript`/`orval` sinh client; Prism mock | Zod chung hai phía, không cần sinh code; muốn OpenAPI phải thêm `zod-to-openapi` hoặc viết tay |
| DOCX → anchors (đoạn + ô bảng) | `python-docx` đọc bảng/ô trực tiếp, trưởng thành | `mammoth` mất cấu trúc ô; phải tự đọc OOXML (JSZip + XML), tốn hơn |
| Unicode tiếng Việt (VAL-02) | `unicodedata.normalize` chuẩn, đã kiểm | `String.normalize` tương đương; không khác biệt |
| Số học (PR-07) | `Decimal` có sẵn | Cần `decimal.js`/`big.js` |
| LLM/AI | Python SDK thuận, MockProvider dễ | SDK Node cũng đủ; không khác biệt thật |
| Một runtime/một deploy | Hai image, Caddy route, CORS/cookie cần xử lý (Q6) | Một image, cùng origin mặc định |
| Ranh giới FE/BE | Cứng; Thiện không chạm backend | Dễ lẫn lộn; cần lint boundary (docs/02 đã lo) |
| Ai viết/ai review | Agent viết; Khải phải đọc được Python mypy-strict | Khải/Thiện quen TS hơn? (chưa có thông tin trong repo) |
| Migration/trigger | Alembic + SQL tay (ổn) | drizzle-kit + SQL tay (ổn) |
| Rủi ro riêng | Hai toolchain trên Windows (uv + pnpm); trùng việc "ai sở hữu `/health`" | Vòng phụ thuộc FE↔BE trong một repo; một lỗi build chặn cả hai |

**Kết luận không thiên vị:** không có lý do kỹ thuật tuyệt đối. Điểm quyết định là (1) **DOCX + Decimal + Unicode** nghiêng Python, (2) **OpenAPI-first** phục vụ hợp đồng với Thiện nghiêng FastAPI, (3) **một deploy / một ngôn ngữ / người review quen TS** nghiêng Next.js. Với 2 dev và deadline 18/11, yếu tố (3) chỉ thắng nếu Khải **không** đọc Python trôi chảy. Hiện tại khuyến nghị giữ FastAPI (Q1), nhưng đây là câu hỏi duy nhất mà đáp án "không" làm đổi cả kế hoạch.

---

## 4. Các quyết định cần Khải xác nhận

> Trả lời "OK" = nhận toàn bộ phương án đầu tiên (khuyến nghị) của mọi Q.

**Q1. Stack backend**
- **(a) Giữ FastAPI ở `apps/api`, FE gọi `/v1` (khuyến nghị).** DOCX/Decimal/Unicode thuận Python; OpenAPI sinh từ Pydantic là hợp đồng cho Thiện. Điều kiện: Khải đọc được Python.
- (b) Quay lại Next.js Route Handlers + Drizzle. Một ngôn ngữ/một deploy, tái dùng docs 02/07 và CI pnpm; tốn thêm cho DOCX (OOXML tay) và Decimal.
- (c) Hybrid: Next.js làm BFF mỏng + FastAPI. Không khuyến nghị: thêm một lớp mà không giải quyết gì ở 4 ngày.

**Q2. Đội và cổng review**
- **(a) 2 dev (Khải backend+AI, Thiện frontend) theo plan v2; Khôi không trong lịch; cập nhật docs/05 sau (khuyến nghị).** Review của Khải đặt ở cuối GĐ3, GĐ6, GĐ8 (mỗi lần ~15 phút trên điện thoại).
- (b) Khôi vẫn là backend như docs/05 (3 dev), plan v2 ghi 2 dev nhầm: Khôi nhận phần Student API/progress/ops từ GĐ9.
- (c) Khải tự review toàn bộ cuối cùng (không cổng giữa): nhanh nhưng rủi ro agent đi lạc 2 ngày.

**Q3. Phạm vi cắt để kịp 18/11 (lát cắt dọc)**
- **(a) Thứ tự: hợp đồng → auth → DOCX/text + anchors → Worksheet end-to-end (generate Mock → validate → review → publish → student) → AT-01..14 → Flashcards → provider thật/6 bài/diff/progress nếu còn giờ (khuyến nghị).** Nhờ vậy 17/11 chắc chắn có một luồng trọn vẹn cho kiểm thử FE.
- (b) Làm đủ prompt theo GĐ 1→10 tuần tự: đúng bản gốc, nhưng nếu trượt, thứ bị bỏ là student/publish, tức là phần Thiện cần nhất cho 18/11.
- (c) Cắt thêm: chỉ nhập text dán, bỏ DOCX. Nhanh hơn ~½ ngày nhưng mất ô bảng, là lõi của bài Địa lí.

**Q4. Hợp đồng API và H1 (14/11)**
- **(a) OpenAPI-first: GĐ3 chỉ cần Pydantic schema + route khai báo (handler trả 501 hoặc dữ liệu tối thiểu) + `examples` đầy đủ từ fixture tay; Thiện dùng Prism + client sinh; v0 gửi tối 14/11, freeze v1 sáng 16/11 (khuyến nghị).** Bỏ "route stub đọc DB seed" vì sẽ bị viết lại ở GĐ6–9.
- (b) Làm đúng prompt: stub trả dữ liệu seed thật. Thiện dùng được server thật sớm hơn nhưng GĐ2+3 chiếm cả ngày.
- (c) Dời H1 sang 15/11 và làm đủ stub: không khuyến nghị, H2 17/11 sẽ gãy.

**Q5. PR-07 và câu hỏi tính toán (`CALCULATE`)**
- **(a) Cho phép số dẫn xuất có `derivation` khai báo (ví dụ `{op: "sum|diff|ratio|percent", operands: [anchor alias hoặc số]}`), server tính bằng `Decimal` và đối chiếu; sai ⇒ VAL-03 BLOCKER (khuyến nghị).** ~40 dòng, giữ được AT-06 mà không chặn bài tập tính.
- (b) Số trong `answer_key` miễn PR-07 nhưng gắn WARNING "chưa kiểm tự động", buộc GV tự kiểm. Nhanh nhất; yếu hơn tinh thần đặc tả ("không gắn nguồn giả").
- (c) Bỏ `CALCULATE` khỏi P0 (chỉ READ_TABLE/COMPARE/EXPLAIN). Gọn nhưng mất kỹ năng chính của bài bảng số liệu.

**Q6. Phiên đăng nhập và origin**
- **(a) Cùng origin qua Caddy (`/v1/*` → api); dev: Next `rewrites` proxy; phiên là cookie session ngẫu nhiên phía server (một bảng `session`, `HttpOnly; Secure; SameSite=Lax`), CSRF bằng header tùy chỉnh + kiểm `Origin`; thu hồi khi logout (khuyến nghị).** Ít mã hơn JWT+refresh xoay vòng, thu hồi thật, không CORS.
- (b) Đúng prompt: JWT 15' + refresh cookie xoay vòng. Cần thêm bảng `refresh_token`, phát hiện tái sử dụng, CORS credentials giữa `:3000` và `:8000`.
- (c) JWT trong header `Authorization`, lưu ở bộ nhớ FE: dễ nhất cho Thiện, nhưng mất khi tải lại và dễ lộ nếu XSS.

**Q7. Mức ép buộc bất biến và hash binding**
- **(a) Ép ở DB + service: hash phủ `kind/payload/cha/transformation/noSourceReason` (B1), `source_hashes` xác định (B2), khóa hàng khi duyệt/publish (B7–B8), trigger chặn sửa block sau publish (B9), trigger chặn UPDATE nội dung `source_*` (B10), role `preclass_app` không UPDATE/DELETE bảng append-only (B11), soft delete (B12) (khuyến nghị).** Thêm khoảng nửa ngày ở GĐ2, nhưng PR-02/PR-05 là lõi bài thi.
- (b) Chỉ làm đúng prompt hiện tại (hash payload, trigger snapshot). Nhanh hơn; còn kẽ hở B1, B7, B9.
- (c) (a) trừ role DB riêng (B11): trigger đã chặn, role để GĐ10.

**Q8. Ai được duyệt và đọc gì**
- **(a) TEACHER duyệt bài **của mình**; REVIEWER (cờ cấu hình, mặc định tắt) duyệt bài được gán qua bảng `lesson_reviewer`; ADMIN xem audit, không sửa; mọi tài nguyên của GV khác → 404 (khuyến nghị).**
- (b) Đúng chữ PR-02: mọi TEACHER/REVIEWER trong trường duyệt mọi bài. Đơn giản hơn nhưng GV B có thể duyệt bài GV A: lỗ hổng IDOR về mặt nghiệp vụ.
- (c) (a) kèm "GV cùng bộ môn đọc bài của nhau (chỉ đọc)": thêm quyền đọc chéo, cần thêm test.

**Q9. Xử lý docs và ADR cũ**
- **(a) Viết `docs/adr/ADR-0010-fastapi-backend.md` (từ D-001, supersedes ADR-0001, một phần 0002/0005/0006/0008), thêm banner "Superseded" đầu docs 01/02/05/06 và `drizzle/README`; không viết lại nội dung (khuyến nghị).** Nhanh, đúng quy tắc "không sửa ADR đã duyệt".
- (b) Viết lại docs 01–07 theo v2. Sạch nhưng tốn ≥ 1 ngày không tạo ra mã.
- (c) Để nguyên, chỉ thêm `docs/v2/`. Rủi ro: agent/người mới đọc docs 02 và làm theo Next.js.

---

## 5. Môi trường máy này: điều chỉnh

### 5.1 Đã kiểm tra

| Mục | Kết quả | Điều chỉnh |
|---|---|---|
| `uv` 0.11.8 | Có. **Python 3.12.13 đã cài sẵn** (cũng có 3.11, 3.13). PATH ưu tiên Python 3.10 | Bỏ `uv python install 3.12`; dùng `uv venv --python 3.12`, mọi lệnh qua `uv run` |
| Console encoding | `sys.stdout.encoding = cp1258` ⇒ **`UnicodeEncodeError` khi in tiếng Việt** (tái hiện khi đọc `.docx` hôm nay) | Đặt `PYTHONUTF8=1` (trong `.claude/settings.json` `env`, và `docs/api/API_GUIDE.md` cho Thiện); `open(..., encoding="utf-8")` ở mọi script |
| Git | `core.autocrlf=true`, **chưa có `.gitattributes`** | Thêm `.gitattributes` **trước mọi commit**: `* text=auto eol=lf`, `*.sh text eol=lf`, `*.docx binary`. Nếu không, `backup.sh`/`entrypoint` bị CRLF và hỏng trong container Linux |
| Docker Desktop | Chạy (engine Linux v29.5.3), 0 container, cổng 5432/8000/3000 **trống** | Giữ cổng mặc định; Postgres dev bind `127.0.0.1:5432` như cũ |
| Testcontainers (Windows) | Được hỗ trợ nhưng chậm, nhạy với Ryuk/npipe | Fixture đọc `TEST_DATABASE_URL`; local dùng DB `preclass_test` trên Postgres của Compose (rollback/template DB), CI dùng service container; Testcontainers là tùy chọn, không phải điều kiện cổng |
| Node 22.18 có, `pnpm` **chưa cài** | `npx @stoplight/prism-cli` chạy được | pnpm là việc của Thiện (`corepack enable`); backend không cần |
| Shell | Bash tool (Git Bash) + PowerShell | Lệnh trong tài liệu viết dạng `uv run ...` thuần, tránh `source venv/bin/activate`, tránh `&&` đặc thù PowerShell 5.1 |
| pre-commit/gitleaks cục bộ | gitleaks cần Go/Docker hook, chậm trên Windows | Chạy gitleaks trong CI; `ruff`/`mypy` chạy trực tiếp bằng `uv run` |
| Compose staging | `web` `depends_on: service_healthy`, Postgres staging **không có healthcheck**; `infra/.env.staging|prod` và `*.example` không tồn tại | Thêm healthcheck + tạo `infra/.env.staging.example`, `.env.prod.example` |

### 5.2 `.claude/settings.json` (cho Remote Control trên iPhone)

Quyền hỏi sẽ **chặn phiên** khi Khải không ở máy. Đề xuất:

- Thêm `"defaultMode": "acceptEdits"` và `"env": {"PYTHONUTF8": "1"}`.
- **Bỏ** `Bash(python *)`, `Bash(py *)`, `Bash(pip *)` (dễ chạy nhầm Python 3.10 hệ thống); giữ `uv *`.
- Thêm `Bash(git branch*)`, `Bash(curl http://localhost*)`, `Bash(npx --yes @stoplight/prism-cli*)`.
- Thêm deny: `Bash(docker compose * down -v*)`, `Bash(docker system prune*)`, `Bash(docker volume rm*)` (mất DB dev/staging), giữ deny hiện có (`git push*`, `reset --hard`, `.env`).
- File này đang untracked: quyết định commit (cả đội dùng chung) hay `.gitignore`.

---

## 6. Kế hoạch thực thi đề xuất

Quy ước: hôm nay **14/11 (T7)**. "Cổng" = điều kiện để sang bước sau. Khải review = trả lời "OK/sửa" trên điện thoại.

| Giai đoạn | Thời điểm | Nội dung | Cổng kiểm tra | Cần Thiện |
|---|---|---|---|---|
| **G0 Chốt** | 14/11 sáng | Khải trả lời Q1–Q9; cập nhật prompt v2 (mục 7); T9 → `in_progress`; `.gitattributes`, `.claude/settings.json` | Prompt v2 đã sửa, không còn đường dẫn cũ | Xác nhận stack FE (Next 15, TanStack Query?), công cụ sinh client, chỗ đặt `apps/web` (hiện rỗng) |
| **GĐ1 Khung** | 14/11 sáng | `apps/api` (uv, FastAPI, config, RFC 9457, `/v1/health`), Compose dev (+api), CI job Python, ADR-0010, `AGENTS.md` | `uv run ruff check . && uv run mypy --strict app && uv run pytest` xanh; `docker compose -f infra/compose.dev.yml up -d` healthy; CI chạy | — |
| **GĐ2 Model** | 14/11 trưa–chiều | Models + Alembic (kèm trigger B9–B10, role B11), `DATA_MODEL.md`, seed **2 bài** + tài khoản; fixture JSON cho ví dụ | Migration up/down sạch; test trigger/append-only; test bất biến APPROVED⇔review_event | Đọc `DATA_MODEL.md` (ý kiến về tên field) |
| **GĐ3 Hợp đồng v0** | 14/11 tối (**H1**) | Pydantic schema, route khai báo, `openapi.json`, `API_GUIDE.md` (luồng S01–S07, bảng mã lỗi 403/404/409/410, ví dụ), Prism | `openapi.json` snapshot test; `prism mock` chạy; **Khải review 15 phút** | **Nhận v0 tối 14/11; phản hồi trước 15/11 22:00** (field thiếu, tên, màn hình cần gì) |
| **Freeze v1** | 16/11 sáng | Gộp phản hồi Thiện; bump `info.version=1.0.0`; sau đó chỉ thêm field | Diff OpenAPI v0→v1 được Khải+Thiện đồng ý; CI chặn đổi tên/xóa | Xác nhận không còn thay đổi chặn |
| **GĐ4 Auth** | 15/11 sáng | Phiên, vai trò, test IDOR cơ bản | Test 10.1 xanh (phần auth/IDOR) | Gọi `/v1/me` qua proxy cùng origin |
| **GĐ5 Sources** | 15/11 | Text + DOCX (đoạn, ô bảng), anchors, revision mới, `PUT /revisions/{id}/sources` | Parse đoạn+bảng; hash đổi khi upload bản mới; zip-bomb bị chặn | S01 trên server thật (local) |
| **GĐ6 Lessons/Blocks** | 15/11 tối–16/11 | Lessons, blocks, provenance, PATCH + transformation + invalidation | AT-03, 04, 08, 09 xanh; **Khải review** | S03 Editor/Inspector |
| **GĐ7 Generate+VAL** | 16/11 | MockProvider (+`MOCK_INJECT`), parser, VAL-01..06 (+stub 07/08/09), derivation (Q5) | AT-01, 02, 05, 06 xanh | S02 Generate, job polling |
| **GĐ8 Review/Publish** | 16/11 tối | Review hash-bound, queue, gate, snapshot, withdraw, new-revision, history cơ bản | AT-10, 11, 12, 14; test song song B7/B8; **Khải review** | S04, S05, S06 |
| **GĐ9 Student** | 17/11 sáng | DTO HS (danh sách trắng), attempts, assignment, (progress nếu kịp) | AT-13 + test PR-08 + test cửa sổ thời gian | S07 (mobile) |
| **GĐ10 Đóng gói** | 17/11 chiều | Compose staging/prod (api+web+caddy, healthcheck, 2 image), RUNBOOK, `scripts/smoke.py`, HANDOFF | `docker compose up` máy sạch + smoke xanh. **Đóng băng tính năng backend 17/11 20:00 (H2)** | Cùng chạy smoke với bản FE build |
| **Mốc 18/11** | 18/11 | Backend trực sửa lỗi; Thiện kiểm thử FE end-to-end | Không thay đổi hợp đồng; lỗi ghi issue `api-change` nếu buộc đổi | Kiểm thử FE (nhóm) |
| **Sau** | 19–20/11 | Flashcards (nếu chưa), provider thật khi có key, 6 bài mock, deploy prod, backup+restore drill | Restore drill thành công trước khi mở dữ liệu thật | Sửa UI |

**Quy tắc tiến độ:** nếu GĐ6 chưa xanh vào 16/11 trưa, cắt theo thứ tự: history diff → progress → derivation (rơi về Q5-b) → Flashcards → DOCX bảng (rơi về text). Không cắt: hash binding, publish gate, PR-08, IDOR.

**Việc cần Thiện (tổng hợp):** xác nhận stack FE; nhận v0 tối 14/11 và phản hồi trước 22:00 15/11; sinh client từ OpenAPI và dùng Prism; cấu hình proxy cùng origin; ghi trong issue `api-change` mọi đề nghị đổi sau freeze; chuẩn bị kiểm thử FE 18/11; `corepack enable` để có pnpm; chuyển `APP_CI_ENABLED=true` khi có lockfile.

---

## 7. Thay đổi sẽ áp vào prompt v2 nếu được duyệt

Mọi thay đổi chỉ trong `docs/v2/CLAUDE_CODE_PROMPT_Backend_v2.md` (và `.env.example`, `.agents/tasks/T9` ở GĐ1). Ký hiệu theo mục 3.

| ID | Mục trong prompt | Thay đổi | Từ |
|---|---|---|---|
| C-01 | Đầu / "Điều chỉnh" | Thêm: dẫn chiếu D-001; xóa `uv python install 3.12` (đã có); thêm `PYTHONUTF8=1`, `.gitattributes` làm việc đầu tiên | §5 |
| C-02 | §0 quy tắc 1, 2, 5; §4 cây; §6 cuối; §9 sau GĐ3; §12 | Thay mọi đường dẫn cũ bằng đường dẫn thật (`docs/v2/…`, `.agents/PROGRESS.md`, `.agents/DECISIONS_AGENT.md`, `.agents/handoffs/T9-backend-v2.md`, `apps/api/openapi/…`, `docs/api/…`) | A1 |
| C-03 | "Điều chỉnh" dòng ADR | `ADR-0001` → `ADR-0010`; agent soạn từ D-001, không tự quyết | A2 |
| C-04 | §4 Đóng gói | Bỏ `docker-compose.yml`; ghi `infra/compose.*.yml` | A3 |
| C-05 | §11 | Hợp nhất với `.env.example` (một `DATABASE_URL`, giữ `AI_ENABLED`, `SESSION_SECRET`, `BACKUP_ENCRYPTION_KEY`, bỏ khóa trùng); `TEST_DATABASE_URL`; `FRONTEND_ORIGIN` chỉ dùng khi dev tách origin | A4, Q6 |
| C-06 | §0 quy tắc 6 | Bỏ "Conventional Commits"; theo style repo | A5 |
| C-07 | §0 quy tắc 3 + §9 | Thêm cổng review Khải (GĐ3, GĐ6, GĐ8), lát cắt dọc Worksheet-first, quy tắc cắt khi trượt, mốc đóng băng 17/11 20:00 | Q2, Q3, §6 |
| C-08 | §6 cuối + §9 GĐ3 | OpenAPI-first + Prism + `examples`; v0 14/11, freeze v1 16/11 sáng; CI chặn đổi tên/xóa field sau freeze | Q4 |
| C-09 | §2 PR-07 + §5 block types | Thêm `derivation` cho số dẫn xuất; parser số VN thống nhất; test bảng riêng | Q5, B16, B17 |
| C-10 | §4 Auth + §5 + §6 | Phiên cookie server-side (hoặc JWT+refresh nếu chọn Q6-b + bảng `refresh_token`), cùng origin qua Caddy, CSRF | Q6, B19 |
| C-11 | §5 `content_block` | Thêm `version`, `deleted_at`; định nghĩa `content_hash` đầy đủ; `source_hashes` | B1–B3, B12 |
| C-12 | §8 Invalidation | Hướng phụ thuộc bắc cầu + cha; chỉ APPROVED → REVIEW_AGAIN; một nơi cập nhật `review_status`; khóa hàng ở review và publish | B4–B8 |
| C-13 | §5, §9 GĐ2 | Trigger khóa block/provenance/lesson_source khi revision ≠ DRAFT; trigger bất biến `source_*`; role DB `preclass_app`/`preclass_migrator` | B9–B11 |
| C-14 | §5 `student_attempt`, `assignment` | `UNIQUE(assignment,student,item)`; bỏ `first_attempt`; `is_correct=null` cho SHORT/rubric; chặn theo `open_at/due_at` | B13–B15 |
| C-15 | §6 | Thêm `PUT /revisions/{id}/sources`; mã 403/404 quy ước (C2); alias anchor `A1..An` cho LLM | B18, B20, C2 |
| C-16 | §2 PR-02, §6 review | Mô hình quyền Q8 (`lesson_reviewer`, tác giả duyệt bài mình); quyền xem progress theo `class_member` | Q8, C1, C4 |
| C-17 | §10.1 PR-08 | DTO danh sách trắng + test snapshot schema HS + test quét | C5 |
| C-18 | §7, §4 job | Job: 1 worker, khôi phục khi khởi động, 1 job/revision, chế độ generate (chưa có block / append); `AI_ENABLED` + bảng `usage_daily`; ghi chú prompt injection | D1–D3, D5 |
| C-19 | §4 DOCX | Hardening zip (magic, giới hạn sau giải nén, từ chối macro); ghi "chưa có malware scan" vào HANDOFF | D4 |
| C-20 | §4 Log | Bộ lọc redaction + test | D6 |
| C-21 | §6 `GET /blocks/{id}/provenance` | Ghi `audit_log` INSPECT_PROVENANCE | D7 |
| C-22 | §3/§4/§9 | Hoãn: provider thật, history diff, progress, VAL-08/09 thực chất, Testcontainers bắt buộc, pre-commit gitleaks; seed 2 bài trước, 6 bài sau; đánh dấu rõ "P0.5" | §3.2E |
| C-23 | §3 "Không làm" | Ghi rõ đã cắt Slides/Visual Story/PPTX/PDF khỏi đặc tả; cần Product ack (không chặn mã) | §3.2E |
| C-24 | §9 GĐ10 + §12 | Compose staging/prod thêm healthcheck, 2 image, file `.env.*.example`; smoke chạy bằng `uv run` | §2.3, §5.1 |

Việc **ngoài prompt** cần Khải duyệt cùng lúc: `.gitattributes`, `.claude/settings.json` (5.2), banner "Superseded" cho docs 01/02/05/06 và `drizzle/README` (Q9), cập nhật `CODEOWNERS`/`dependabot.yml`, và việc mở đầu `T9` bằng `in_progress`.

---

## 8. Hệ quả và rollback

- Lợi ích: một hợp đồng API duy nhất (OpenAPI) cho Thiện; PR-02/PR-05 được DB bảo vệ; tiến độ có đường cắt rõ ràng.
- Chi phí/rủi ro: hai toolchain (uv + pnpm); lịch vẫn sát; Q5-a và Q7-a thêm ~1 ngày công gộp vào GĐ2/GĐ7, đã bù bằng cắt phạm vi ở Q3/Q4.
- Rollback: nếu sau GĐ3 Khải thấy Python khó review hoặc hợp đồng không dùng được cho Thiện, quay Q1-b: Pydantic schema và `DATA_MODEL.md` chuyển thành Zod/Drizzle (thiết kế, hash, trigger SQL và test AT tái dùng nguyên).
- Không có mã nào bị bỏ nếu rollback (chưa có mã).
