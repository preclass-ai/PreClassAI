# API guide cho frontend (v0, gửi 14/11 · freeze v1 sáng 16/11)

Hợp đồng chính thức: [`apps/api/openapi/openapi.json`](../../apps/api/openapi/openapi.json) (sinh từ code, CI chặn lệch). Tài liệu này là hướng dẫn đọc nhanh. Mô hình dữ liệu: [`DATA_MODEL.md`](DATA_MODEL.md).

> **Trạng thái:** mọi endpoint đã có schema + ví dụ. **Đã chạy thật (tới GĐ8):** auth, nguồn (text/DOCX), lesson, block, provenance, generate (MockProvider), validate, review, publish gate, new-revision, withdraw, giao bài, danh sách bài giao của lớp. **Không còn endpoint 501** (GĐ9 đã xong). **Hãy dựng FE trên Prism mock** (bên dưới). Sau freeze v1 chỉ *thêm* field, không đổi tên/xóa field. Mọi thay đổi hợp đồng báo Khải trước.

## 1. Chạy mock và sinh client

```bash
# mock theo ví dụ trong openapi.json (cổng 4010)
npx @stoplight/prism-cli mock -p 4010 apps/api/openapi/openapi.json

# sinh kiểu TypeScript
npx openapi-typescript apps/api/openapi/openapi.json -o apps/web/src/api/schema.d.ts
```

Prism trả ví dụ của schema (id trùng id seed). Muốn thử mã lỗi: `curl -H 'Prefer: code=409' ...`.

## 2. Quy ước chung

- Base path `/v1`. JSON **camelCase**. Id là UUID. Giờ ISO-8601 có múi giờ.
- **Xác thực:** cookie session `preclass_session` (HttpOnly, SameSite=Lax) do `POST /v1/auth/login` đặt. Gọi `fetch(url, { credentials: "include" })`. Không có JWT, không có `/auth/refresh`.
- **CSRF:** mọi request không phải GET gửi header `X-PreClass-CSRF: 1`; thiếu → 403 `CSRF`.
- **Cùng origin:** production dùng Caddy (`/v1/*` → api, còn lại → web). Dev: cấu hình Next `rewrites` `source: "/v1/:path*"` → `http://localhost:8000/v1/:path*`.
- **Lỗi:** `application/problem+json` `{type,title,status,detail,code,errors?}`. **Luôn rẽ nhánh theo `code`**, không theo `title/detail` (tiếng Việt, có thể đổi). `errors[]` chỉ có `loc` và `type` (không lặp lại giá trị người dùng gửi).
- **Khóa lạc quan:** các lệnh sửa gửi `version`; cũ → `409 VERSION_CONFLICT` (tải lại rồi thử lại).
- **Quyền:** sai vai trò → `403 FORBIDDEN_ROLE`; tài nguyên của người khác/lớp khác → `404 NOT_FOUND` (không phân biệt "không có" và "không phải của bạn").
- **Danh sách:** `{items: [...], nextCursor: null}` (cursor chưa dùng ở v1).
- Block trả **phẳng** (`parentId`, `position`); tự dựng cây.

## 3. Luồng gọi theo màn hình

| Màn | Việc | Gọi |
|---|---|---|
| **Đăng nhập** | Vào hệ thống | `POST /auth/login` `{identifier, password}` → `UserOut`; `GET /me` khi tải lại trang; `POST /auth/logout` |
| **S01 Source Library** | Nhập nguồn | `GET /sources`; `POST /sources` (dán văn bản) hoặc `POST /sources/docx` (multipart: `file`, `title`, `licenseNote?`, `visibility?`) → có ngay `extractStatus`, `anchorCount`; `POST /sources/{id}/revisions[/docx]` để tải bản mới; `GET /source-revisions/{id}/anchors` |
| **S02 Generate** | Tạo lesson + sinh bản nháp | `POST /lessons` `{title, grade, goal, sourceRevisionIds}` → `LessonOut.currentRevision.id` = `revisionId`; `POST /lessons/{id}/generate` `{outputType, nItems, focusSkills, mode}` → 202 `{jobId}`; poll `GET /jobs/{id}` mỗi 1–2 s tới `SUCCEEDED/FAILED`. AI tắt → `503 AI_DISABLED` |
| **S03 Editor + Source Inspector** | Sửa block, xem nguồn | `GET /revisions/{rid}/blocks`; `PATCH /blocks/{id}` `{payload, version}`; `POST /revisions/{rid}/blocks`; `DELETE /blocks/{id}`; **Inspector:** `GET /blocks/{id}/provenance` (link + trích đoạn + vị trí, lịch sử biến đổi, kết quả validation, các lần duyệt); sửa nguồn: `PUT /blocks/{id}/provenance` `{links}` hoặc `{noSourceReason}`; `POST /revisions/{rid}/validate`; đổi nguồn của cả bài (DRAFT): `PUT /revisions/{rid}/sources` |
| **S04 Review Queue** | Duyệt từng block | `GET /revisions/{rid}/review-queue?status=FLAGGED,REVIEW_AGAIN,UNREVIEWED`; `POST /blocks/{id}/reviews` `{action, contentHash, note?}`. **Không có "duyệt tất cả".** `409 STALE_REVIEW` → tải lại block |
| **S05 Publish Gate** | Xuất bản | `GET /revisions/{rid}/publish-check` (checklist, không ghi); `POST /revisions/{rid}/publish` `{confirmChecked: true, version}`; chặn → `409 PUBLISH_BLOCKED` + `blockIds` (xem `errors`/`detail` ở `publish-check`); `POST /published/{pid}/assignments` `{classId, openAt, dueAt}`; `POST /published/{pid}/withdraw` `{reason}` |
| **S06 History** | Lịch sử | `GET /lessons/{id}/history`; sửa bài đã xuất bản: `POST /revisions/{rid}/new-revision` |
| **S07 Student** | Học sinh làm bài | `GET /student/assignments`; `GET /student/assignments/{id}` (chỉ nội dung đã lọc); `POST /student/assignments/{id}/attempts` `{itemId, answer, requestId}` → `isCorrect` + `explanation` **chỉ sau khi nộp**. Đã thu hồi → `410 WITHDRAWN` |
| GV theo dõi | Lớp | `GET /classes`; `GET /classes/{cid}/assignments`; `GET /classes/{cid}/assignments/{aid}/progress` |
| Admin | Audit | `GET /admin/audit-logs` |

Quy tắc UI quan trọng:
1. **Có nguồn ≠ đúng.** Hiển thị `reviewStatus` (đã kiểm/duyệt chưa) **tách biệt** với số nguồn (`linkCount`) / `transformation`.
2. Block `AI_PROPOSED` không nguồn phải hiện `noSourceReason`.
3. Học sinh **không bao giờ** thấy provenance/review/validation/đáp án/giải thích trước khi nộp câu đó (server đã lọc, FE đừng cố gọi). `GET /blocks/{id}/provenance` với vai HS trả **404 NOT_FOUND** (PR-08), không phải 403.
4. Trước khi gọi `reviewBlock` luôn gửi `contentHash` của đúng bản đang hiển thị.

## 4. Bảng mã lỗi (`code`)

| code | HTTP | Khi nào |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Body/query sai schema; `errors[].loc` chỉ vị trí |
| `UNAUTHENTICATED` | 401 | Chưa đăng nhập / phiên hết hạn / đã logout |
| `INVALID_CREDENTIALS` | 401 | Sai tài khoản hoặc mật khẩu |
| `RATE_LIMITED` | 429 | Đăng nhập sai nhiều lần |
| `CSRF` | 403 | Thiếu header `X-PreClass-CSRF` hoặc `Origin` lạ |
| `FORBIDDEN_ROLE` | 403 | Đúng người đăng nhập nhưng sai vai trò (vd học sinh gọi route giáo viên) |
| `NOT_FOUND` | 404 | Không có hoặc không thuộc về bạn / lớp bạn; học sinh trước `openAt` |
| `VERSION_CONFLICT` | 409 | `version` cũ |
| `STALE_REVIEW` | 409 | `contentHash` cũ khi duyệt |
| `REVISION_LOCKED` | 409 | Sửa bản đã PUBLISHED/SUPERSEDED |
| `PUBLISH_BLOCKED` | 409 | Gate chưa đạt; kèm `blockIds` |
| `JOB_ALREADY_RUNNING` | 409 | Đang có job generate cho revision |
| `REVISION_NOT_EMPTY` | 409 | Generate `mode=initial` khi đã có block (dùng `append`) |
| `NOT_PUBLISHED`, `DRAFT_EXISTS` | 409 | `new-revision` sai trạng thái |
| `ASSIGNMENT_CLOSED` | 409 | Nộp sau `dueAt` |
| `ALREADY_ANSWERED` | 409 | Câu này đã trả lời (mỗi câu một lần) |
| `ANCHOR_NOT_IN_LESSON` | 422 | Link tới anchor không thuộc nguồn của bài |
| `WITHDRAWN` | 410 | Bản đã thu hồi (HS mở bài); 409 khi giao bài từ bản đã thu hồi |
| `AI_DISABLED` | 503 | `AI_ENABLED=false` hoặc hết ngân sách token ngày |
| `NOT_IMPLEMENTED` | 501 | **Chỉ ở v0**, handler chưa làm |

## 5. Tài khoản seed (chỉ dev; mật khẩu `preclass-demo`)

| Đăng nhập (`identifier`) | Vai trò |
|---|---|
| `gv.dia@preclass.local` | Giáo viên (lớp 10A1 + 11A1, 5 bài) |
| `gv.khac@preclass.local` | Giáo viên khác (thử 404) |
| `reviewer@preclass.local` | Reviewer |
| `admin@preclass.local` | Admin |
| `HS10-01` … `HS10-15` | Học sinh lớp 10A1 |
| `HS11-01` … `HS11-15` | Học sinh lớp 11A1 |

Bài seed `dan-so-vung` (lớp 10) đã **PUBLISHED** và giao cho 10A1 → dùng cho S07. Bài `dien-tich-rung` có đủ trạng thái block để thử S03/S04. Toàn bộ số liệu là **DỮ LIỆU MINH HỌA** (giả).

## 6. Ví dụ (lấy từ seed)

Đăng nhập:

```http
POST /v1/auth/login
{"identifier": "gv.dia@preclass.local", "password": "preclass-demo"}
→ 200  Set-Cookie: preclass_session=…; HttpOnly
{"id":"eb9a9e82-7954-5e82-a597-16c6123031ff","role":"TEACHER","displayName":"Cô Địa Lí (minh họa)","email":"gv.dia@preclass.local","loginCode":null,"classIds":["d97fbc44-edb6-5333-b65d-1427e836354c","cf4d05fd-9a71-57a0-9eaa-421c08c3c74c"]}
```

Duyệt một block (hash cũ → lỗi):

```http
POST /v1/blocks/{blockId}/reviews     X-PreClass-CSRF: 1
{"action":"APPROVE","contentHash":"<hash đang hiển thị>","note":null}
→ 201 {"block": {…, "reviewStatus":"APPROVED"}, "reviewEventId":"…"}
→ 409 {"code":"STALE_REVIEW", "status":409, …}
```

Học sinh nộp câu (`HS10-01`, bài `dan-so-vung`):

```http
POST /v1/student/assignments/d186c051-eff2-5d04-8e6a-a01fe9880b24/attempts
{"itemId":"<id câu MCQ>","answer":{"choice":"A"},"requestId":"<uuid mới mỗi lần bấm Nộp>"}
→ 201 {"itemId":"…","isCorrect":true,"explanation":"Đồng bằng sông Hồng có số dân cao nhất (23,2 triệu người), cao hơn Đông Nam Bộ (17,8 triệu người)."}
```

Các ví dụ đầy đủ cho từng endpoint nằm trong `openapi.json` (`components.schemas.*.examples`) và Prism trả chúng.

## 7. Khác với đặc tả gốc (đã chốt ở D-001, FE cần biết)

- Không có `/auth/refresh` (cookie session thay JWT).
- Upload DOCX tách thành `POST /sources/docx` và `POST /sources/{id}/revisions/docx` (multipart) vì một path không khai báo được cả JSON lẫn multipart.
- Thêm `PUT /revisions/{id}/sources`, `GET /classes/{id}/assignments`, `GET /admin/audit-logs`.
- Tải bản nguồn mới **không** tự đổi bài đang soạn: lesson ghim source revision; bài chỉ hiện `newerSourceAvailable=true`.
  Khi GV gọi `PUT /revisions/{id}/sources {sourceRevisionIds, version}` (chỉ DRAFT, **một transaction**): mọi block có link tới anchor của revision cũ, block phụ thuộc chúng (bắc cầu) và block cha trực tiếp chuyển `REVIEW_AGAIN` (ghi `transformation_event` `SOURCE_REPLACED`); link nào có anchor trùng `excerptHash` ở bản mới được trỏ sang anchor mới (`VERIFIED`), còn lại thành `UNRESOLVED` (GV gán lại qua `PUT /blocks/{id}/provenance`). Duyệt cũ không còn hiệu lực (duyệt gắn hash nguồn). Response: `{revision, matchedLinks, unresolvedLinks}`. Bài đã PUBLISHED không bị ảnh hưởng (409 `REVISION_LOCKED`).
- Chưa có cursor pagination (envelope `{items,nextCursor}` đã có sẵn).
- Payload trong block dùng camelCase (`itemType`, `rubricPoints`), khác snake_case ghi trong đặc tả.

## 8. Cập nhật GĐ5–8 (mã mới và hành vi cần biết)

| code | HTTP | Khi nào |
|---|---|---|
| `INVALID_FILE`, `FILE_TOO_LARGE`, `MACRO_REJECTED`, `EMPTY_SOURCE` | 422 | Upload DOCX hỏng / quá 10 MB / có macro / không có chữ |
| `LICENSE_REQUIRED` | 422 | Nguồn `SCHOOL` thiếu `licenseNote` |
| `SOURCE_UNCHANGED` | 409 | Bản nguồn mới trùng hệt bản hiện tại |
| `PAYLOAD_INVALID`, `PARENT_NOT_FOUND`, `PROVENANCE_INVALID` | 422 | Sai payload theo `kind` (khóa lạ bị từ chối; khóa `null` được bỏ qua), khối cha không tồn tại, gửi cả/không gửi `links`/`noSourceReason` |
| `APPROVE_BLOCKED` | 409 | Duyệt (APPROVE) khối còn lỗi chặn; vẫn được REJECT / REQUEST_CHANGES |
| `CONFIRM_REQUIRED` | 422 | Publish mà `confirmChecked` ≠ true |
| `PUBLISH_BLOCKED` | 409 | Gate chưa đạt. Body có thêm **`blockIds`**: các khối chặn xuất bản |
| `ALREADY_WITHDRAWN` | 409 | Thu hồi lần hai |
| `GRADE_MISMATCH`, `INVALID_WINDOW` | 422 | Giao bài sai khối lớp / `dueAt` ≤ `openAt` |

Quy tắc hành vi:
- `POST /blocks/{id}/reviews`: `contentHash` phải là hash đang hiển thị, sai → 409 `STALE_REVIEW` và không ghi gì. `APPROVE`→`APPROVED`, `REJECT`→`REJECTED`, `REQUEST_CHANGES`→`REVIEW_AGAIN`. Reviewer chỉ dùng được khi bật `REVIEWER_ENABLED` và được gán bài (mặc định tắt: 403 `FORBIDDEN_ROLE`).
- `GET /revisions/{id}/publish-check` tính lại toàn bộ rule tại thời điểm gọi (không ghi gì): 4 mục `ALL_APPROVED`, `NO_BLOCKERS`, `SOURCES_VALID`, `HAS_ITEMS`, mỗi mục kèm `blockIds`.
- Publish tạo snapshot bất biến, khóa revision (sửa/duyệt → 409 `REVISION_LOCKED`), đánh bản xuất bản trước của bài là `SUPERSEDED` (bản cũ vẫn dùng được cho bài đã giao). `version` là `currentRevision.version` của bài.
- Sửa sau khi xuất bản: `POST /revisions/{id}/new-revision` sao chép block, nguồn, link và phụ thuộc sang bản DRAFT mới; **duyệt không mang theo** (các khối về `AUTO_CHECKED`/`FLAGGED` sau khi chạy validation). Mỗi bài chỉ có một bản nháp (`DRAFT_EXISTS`).
- Thu hồi lưu lý do cùng bản xuất bản và ghi audit `WITHDRAW` (audit không chứa lý do). Học sinh mở bản đã thu hồi sẽ nhận 410 (GĐ9).
- AI sinh nội dung: `POST /lessons/{id}/generate` → 202 `{jobId}` rồi poll `GET /jobs/{id}`. Khối do AI sinh không bao giờ `APPROVED`. `AI_ENABLED=false` hoặc hết ngân sách token ngày → 503 `AI_DISABLED`.

## 9. Học sinh và tiến độ (GĐ9)

| code | HTTP | Khi nào |
|---|---|---|
| `WITHDRAWN` | 410 | Học sinh mở / nộp vào bài đã bị thu hồi (AT-12) |
| `ASSIGNMENT_CLOSED` | 409 | Nộp sau `dueAt` (vẫn đọc được bài) |
| `ALREADY_ANSWERED` | 409 | Câu này đã trả lời bằng `requestId` khác |

- Chỉ nội dung từ **snapshot đã xuất bản**; DTO whitelist: không có đáp án, rubric, derivation, provenance, review, validation. `card_back` không bao giờ nằm trong danh sách khối.
- Trước `openAt`, hoặc học sinh không thuộc lớp → **404** (không lộ tồn tại). Sai vai trò → 403 `FORBIDDEN_ROLE`.
- `POST .../attempts`: mỗi (bài giao, học sinh, câu) một lần; trùng `requestId` trả lại kết quả đã lưu (idempotent). MCQ so `choice`, NUMERIC so `value` theo `tolerance`, SHORT không chấm (`isCorrect: null`). Lời giải chỉ trả sau khi trả lời.
- `GET /classes/{id}/assignments/{aid}/progress`: chỉ giáo viên của lớp đó, chỉ số tổng hợp (không có tên/đáp án từng học sinh); `completedCount` / `inProgressCount` là số học sinh đã làm hết / mới làm một phần.
- `GET /classes/{id}/assignments/{aid}/results.csv`: chỉ giáo viên của lớp đó (khác lớp → 404). Bảng giống trang câu trả lời Google Form: mỗi học sinh của lớp một dòng theo **mã** đăng nhập/khảo sát (không có họ tên, sắp theo mã, không xếp hạng), trạng thái, số câu đã làm/đúng, rồi câu trả lời và Đúng/Sai từng câu. UTF-8 có BOM cho Excel; ô bắt đầu bằng `= + - @` được thêm `'`. Ghi audit `EXPORT_RESULTS`.
- Chưa làm: thẻ ghi nhớ (flashcard) chưa có luồng trả lời riêng.

## 10. Khách khảo sát (ẩn danh) — Pha 0

Bật bằng env `GUEST_ACCESS_ENABLED=true` (mặc định tắt → mọi endpoint khách trả **404**). Lớp khảo sát `GUEST_CLASS_CODE` (mặc định `KS`) do `python -m seed.survey` tạo và giao sẵn mọi bài đã xuất bản.

| Endpoint | Ghi chú |
|---|---|
| `GET /v1/auth/config` → `{guestEnabled}` | Công khai; FE dùng để hiện nút "Vào làm thử" |
| `POST /v1/auth/guest` `{lessonKey?}` → 201 `{user, surveyCode, assignmentId?}` | Tạo tài khoản STUDENT ẩn danh (không tên/email/mật khẩu/IP), set cookie phiên **14 ngày**. `lessonKey` là slug bài (vd `dan-so-vung`): trả `assignmentId` để mở thẳng bài. 429 `RATE_LIMITED` theo IP thật (`GUEST_CREATE_PER_HOUR`, mặc định 60: một lớp dùng chung Wi-Fi chỉ có một IP), 503 `GUEST_CAPACITY` (`GUEST_MAX_ACTIVE`, mặc định 500) / `GUEST_NOT_CONFIGURED` |
| `POST /v1/auth/guest/resume` `{surveyCode}` | Mất cookie / đổi máy; 5 mã sai / 15 phút / IP → 429 |
| `GET /v1/admin/survey/export.csv` (ADMIN, TEACHER) | `survey_code, lesson, item, first_attempt_is_correct, answered_at_utc`; không cột định danh nào khác |

- `UserOut` có thêm `isGuest`, `surveyCode`. Khách là STUDENT: route giáo viên/admin trả 403, PR-08 giữ nguyên (provenance của khách → 404). Mã khách không đăng nhập được bằng `/auth/login`.
- Dọn dẹp thủ công: `scripts/ops/purge_guests.py --dry-run`. Khách đã có bài làm không xóa được (bảng attempt chỉ-thêm), nên chỉ bị vô hiệu hóa.

## 11. Bảo mật khi triển khai (pre-launch)

- **Mật khẩu seed:** `APP_ENV=demo` yêu cầu `SEED_TEACHER_PASSWORD`, `SEED_REVIEWER_PASSWORD`, `SEED_ADMIN_PASSWORD` (≥ 12 ký tự). Thiếu thì **không tạo tài khoản** và log cảnh báo (API vẫn khởi động). Học sinh seed: `SEED_STUDENT_PASSWORD` nếu đặt, nếu không thì mật khẩu ngẫu nhiên bị bỏ đi (không đăng nhập bằng mật khẩu được, chỉ dùng khách). Dev/CI vẫn dùng `SEED_PASSWORD` (mặc định `preclass-demo`). Đổi mật khẩu tài khoản đã có: `scripts/ops/rotate_passwords.py`.
- **Đăng nhập ADMIN:** 3 lần sai / 15 phút (GV/HS: 5 lần / 5 phút). Mọi thao tác admin (`GET /admin/audit-logs`, `GET /admin/survey/stats`, `GET /admin/survey/export.csv`) ghi audit (`ADMIN_VIEW_AUDIT_LOGS`, `ADMIN_VIEW_SURVEY_STATS`, `EXPORT_SURVEY`).
- **`GET /admin/survey/stats`** (ADMIN): `{activeGuests, createdLastHour, maxActive, createPerHourPerIp}`. Log cảnh báo (chỉ số đếm, không IP/mã) khi dùng ≥ 80% `GUEST_CREATE_PER_HOUR` của một client hoặc `GUEST_MAX_ACTIVE`.
- **`/docs` và `/v1/openapi.json`:** `DOCS_ACCESS=open|staff|off`. Mặc định `open`, riêng `APP_ENV=production` mặc định `off`. `staff` = chỉ GV/người duyệt/admin đã đăng nhập (người khác: 404, chưa đăng nhập: 401).
- **Header API:** mọi phản hồi `X-Content-Type-Options: nosniff`; mọi `/v1/*` trừ health `Cache-Control: no-store`.
- **DOCX:** ≤ 10 MB tải lên, ≤ 20 MB giải nén, ≤ 1000 thành phần, tỉ lệ nén ≤ 100:1; từ chối macro (`.docm`, `vbaProject`), đối tượng nhúng/ActiveX và liên kết tới nội dung ngoài (chỉ cho phép hyperlink): `422 EXTERNAL_CONTENT_REJECTED`.

## 12. Nạp nguồn từ tệp DOCX, PDF, XLSX, PPTX

`POST /v1/sources/file` (multipart: `file`, `title`, `licenseNote?`, `visibility?`; TEACHER). Loại tệp lấy từ **magic bytes** và `[Content_Types].xml`, bỏ qua tên và `Content-Type` do client gửi. `/sources/docx` cũ vẫn dùng được.

- Giới hạn (env `SOURCE_*`, xem RUNBOOK): 10 MB; ≤ 1000 entry, ≤ 20 MB giải nén, tỉ lệ nén ≤ 100; PDF ≤ 50 trang; XLSX ≤ 5 sheet × 2000 ô; PPTX ≤ 60 slide; parse trong tiến trình con, tối đa 30 s.
- Locator của anchor: PDF `{page, para}` (đều bắt đầu từ 1); XLSX `{sheet, row, col, header?}` (row/col bắt đầu từ 0, `header` là tiêu đề cột của ô số); PPTX `{slide, shape, para}` hoặc `{slide, shape, row, col}` (slide từ 1, còn lại từ 0). Số trong ô Excel chuẩn hóa thành chữ dạng Việt ("23,2"), `numbers[]` vẫn là số.
- Excel: chỉ đọc giá trị đã lưu, không bao giờ tính công thức.
- Lỗi 422 (`code`): `FILE_TOO_LARGE`, `SOURCE_TOO_LARGE`, `INVALID_FILE`, `MACRO_REJECTED`, `EXTERNAL_CONTENT_REJECTED`, `ACTIVE_CONTENT_REJECTED` (PDF có JavaScript/đính kèm), `PARSE_TIMEOUT`, `EMPTY_SOURCE`, `LICENSE_REQUIRED`.
- PDF scan (không có lớp chữ, không OCR): **201** với `latestRevision.extractStatus = "FAILED"`, `extractError = "SCANNED_PDF"`, `anchorCount = 0`. Dùng nguồn FAILED để tạo bài / đổi nguồn → 422 `SOURCE_NOT_READABLE`.
## 13. Habit (CHAT_ENABLED, mặc định tắt; ADR-0012)

Khi tắt: mọi route dưới đây trả 404 và `GET /v1/auth/config` có `chatEnabled:false` (UI ẩn Habit). Chỉ STUDENT, chỉ bài của lớp mình (khác → 404).

- `GET /v1/student/assignments/{id}/habit` → `{streak, todayGoal, todayDone, badges[{code,label}], hintsAvailable[{itemId,hintsUsed,hintsMax}]}`. Streak = số ngày liên tiếp (giờ Asia/Ho_Chi_Minh) có ≥ 1 câu đã nộp; hôm nay chưa nộp thì streak vẫn tính đến hôm qua.
- `POST /v1/student/assignments/{id}/chat` `{itemId, action: hint|ask|explain, message?, requestId}` → `{reply, hintLevel, sourceRefs[{blockId,label,excerpt}], blockedReason?}`.
  - `hint`: bậc 1→2→3 rồi giữ 3. Sau khi nộp câu đó → 409 `ALREADY_ANSWERED`.
  - `ask`: `message` bắt buộc, ≤ 300 ký tự (422). Từ chối bằng câu mẫu kèm `blockedReason` ∈ `INJECTION | ANSWER_REQUEST | CONFIRM_OPTION | UNSAFE | OFFTOPIC`.
  - `explain`: chỉ sau khi chính học sinh đã nộp câu đó, nếu không 409 `NOT_ANSWERED`.
  - 429 `CHAT_LIMIT` khi quá `CHAT_MAX_PER_ITEM` (6) hoặc `CHAT_MAX_PER_DAY_PER_STUDENT` (30). Gửi lại cùng `requestId` trả phản hồi đã lưu, không tính hạn mức (`sourceRefs` rỗng khi phát lại).
- **HABIT AI v2 (chỉ thêm field).** Yêu cầu `chat` nhận thêm `quick` (`start`, `where_data`, `formula`, `teacher`) cùng `action=ask`: nút gợi ý nhanh, không qua bộ phân loại câu tự do, không dùng hết 3 gợi ý (`start`=bậc 1, `where_data`=bậc 2, `formula`=bậc 3, `teacher`=nhắc hỏi thầy cô). Phản hồi thêm `suggestions[{id,label}]` (4 nút sau khi từ chối hoặc ngoài phạm vi, trừ nội dung không phù hợp), `extra` (phần "gợi ý thêm" khi `CHAT_MODE=llm` và `CHAT_AI_EXTRA=true`, kiến thức chung CHƯA được giáo viên kiểm chứng, bị bỏ nếu không qua bộ lọc), và `sourceRefs` chỉ còn tối đa 1 khối (nhãn hiển thị "Tài liệu giáo viên đã duyệt"). Câu hỏi chung về cách làm ("bắt đầu", "làm sao", "không hiểu", "số liệu nằm ở đâu", "công thức") nay nằm trong phạm vi và trả gợi ý tương ứng.
- `GET /v1/admin/survey/export.csv` thêm cột `hints_used, max_hint_level, chat_asks, used_explain, blocked_count` (chỉ số đếm). `GET /v1/admin/survey/stats` thêm `chatTotal, chatFallbackRate, chatBlocked{reason:n}, chatTokensIn, chatTokensOut`.

## 14. Cá nhân hóa do học sinh chọn (PERSONALIZATION_ENABLED, mặc định tắt; ADR-0013)

`GET /v1/auth/config` còn có `chatMode` (rule|llm) và `aiProvider` (tên máy chủ AI khi dùng llm, không bao giờ có khóa hay đường dẫn) cho trang `/du-lieu`.

Khi tắt: các route dưới đây trả 404 và `GET /v1/auth/config` có `personalizationEnabled:false` (UI ẩn). Chỉ STUDENT, chỉ dữ liệu của chính em. Hệ thống **không** có trường nào về tâm lý, sức khỏe hay tính cách.

- `GET /v1/student/preferences` → `{preferences: {key: value}}` (chỉ các lựa chọn đang bật; thiếu khóa = tắt).
- `PUT /v1/student/preferences` `{preferences: {key: "on"|"off"|"5"|"10"}}`: cập nhật từng phần, `off` xóa lựa chọn. Khóa: `chia_nho_tung_buoc`, `uu_tien_bang_so_lieu`, `uu_tien_giai_thich`, `nhac_tien_do` (`on`/`off`), `hen_gio_tap_trung` (`5`/`10`/`off`), `focus_mode_used` (dấu "đã dùng chế độ tập trung" để khảo sát đếm). Khóa lạ hoặc giá trị sai kiểu → 422.
- `DELETE /v1/student/preferences`: tắt hết.
- `GET .../habit` thêm cho mỗi câu `advice` (`REVIEW` = nên xem lại nội dung bài trước, kèm `preview` là Gợi ý 1 mở sẵn và **không** tính là đã dùng gợi ý; `QUIET` = kỹ năng này đang ổn, giảm nhắc; `null` = không có lời khuyên). Tính bằng luật từ kết quả lần làm đầu và số lần dùng gợi ý theo kỹ năng của chính em (`REVIEW`: ≥ 2 câu và sai ≥ 50%; `QUIET`: ≥ 3 câu và ≥ 80% đúng ngay không gợi ý), không lưu kết luận.
- `POST .../chat`: `chia_nho_tung_buoc` rút gợi ý còn một câu ngắn; `uu_tien_bang_so_lieu` làm gợi ý bậc 2 nhắc bảng số liệu trước. Chỉ đổi cách diễn đạt, mọi quy tắc không lộ đáp án giữ nguyên.
- `GET /v1/admin/survey/export.csv` thêm `pref_chia_nho, pref_hen_gio_phut, pref_bang_so_lieu, pref_giai_thich, pref_nhac_tien_do, focus_mode_used` (cờ 0/1; `pref_hen_gio_phut` là 0, 5 hoặc 10).

## 15. Góc nhìn giáo viên (chỉ thêm)

- `GET /v1/classes/{classId}/assignments/{assignmentId}/insights` (TEACHER của lớp; người khác 404, học sinh 403): `themes[{key,label,count,examples}]` (câu hỏi HABIT AI nhóm bằng luật, không dấu và có dấu đều nhận), `items[{position,stem,skill,answeredCount,firstAttemptCorrectRate,hintsUsed,asks}]`, `totalQuestions`, `askingStudents` (số em đã hỏi, không nói là ai), `focusSkills` (kỹ năng của câu có tỉ lệ đúng lần đầu thấp nhất, tối đa 2), `canPractice` (người gọi là tác giả bài), `lessonId`, `publishedRevisionId`, `llmAvailable`. **Ẩn danh:** không có id, tên, mã đăng nhập hay mã khảo sát; văn bản câu hỏi đã được che số điện thoại, email, địa chỉ lúc lưu.
- `POST .../insights/analyze` (nút "AI phân tích"): `{topics[3..5], generatedBy: rule|llm}`. Mặc định tổng hợp bằng luật. Khi `CHAT_MODE=llm` gọi model một lần (cache 10 phút, tính vào `CHAT_DAILY_TOKEN_BUDGET`, chỉ gửi chủ đề, ví dụ và tỉ lệ ẩn danh); lỗi hoặc hết ngân sách thì dùng luật.
- "AI gợi ý bài tập thêm" không có endpoint riêng: giao diện dùng `POST /v1/revisions/{id}/new-revision` (hoặc bản nháp sẵn có) rồi `POST /v1/lessons/{id}/generate` với `mode=append`, `focusSkills` từ `focusSkills` ở trên. Khối AI tạo ra vẫn là AI_PROPOSED, qua VAL-01..10 và phải được giáo viên duyệt như mọi khối; giao bài vẫn là bước riêng.
- **Mã lỗi đổi:** nộp sau hạn trả 409 `PAST_DUE` (trước đây `ASSIGNMENT_CLOSED`); học sinh vẫn xem được bài và lời giải. Giao diện chấp nhận cả hai mã.
- Học sinh thấy hạn nộp dạng dd/mm/yyyy ở mọi lớp (kể cả lớp khảo sát); giáo viên có thể chọn "Ngày học" để đặt hạn vào 23:59 của ngày trước đó (chỉ ở giao diện, API vẫn nhận `dueAt`).

## 16. Giáo án CV 5512 (chỉ thêm)

Chỉ TEACHER là chủ giáo án (người khác 404, học sinh 403).

- `POST /v1/lesson-plans` (multipart `file`, DOCX hoặc PDF có chữ): **202 kèm job ngay** (dưới 2 giây); việc đọc chạy nền trong tiến trình con (tối đa 120 giây, `PARSE_TIMEOUT`). Một tệp nhiều bài là nhiều giáo án; chữ ký và tên giáo viên bị loại. 422 ngay: `UNSUPPORTED_FILE`, `FILE_TOO_LARGE`, `INVALID_FILE`. 409 `PARSE_BUSY` khi giáo viên đang có một job chạy. Lỗi khi đọc (`SCANNED_PDF`, `PARSE_TIMEOUT`, `EMPTY_SOURCE`, `SOURCE_TOO_LARGE`) nằm trong job (`state=failed`, `errorTitle` tiếng Việt). Tệp lưu thành một nguồn riêng tư (neo có `locator.type`).
- `GET /v1/lesson-plans/jobs/{id}` và `GET /v1/lesson-plans/jobs/latest`: `state` queued|parsing|done|failed, `page`/`pages` (đang đọc trang x/y, ước lượng), `planIds` khi xong. Job nằm trong DB nên tải lại trang vẫn thấy; khởi động lại máy chủ làm job đang chạy thành failed (`RESTART`).
- `GET /v1/lesson-plans/competencies`: danh mục năng lực theo môn. `PUT /v1/lesson-plans/{id}/mcqs/{mcqId}/competency` `{competencyCode|null}` (422 `INVALID_COMPETENCY`). `PUT /v1/blocks/{id}/competency` (tác giả; là metadata, không nằm trong hash nên không reset duyệt). Khi tạo bài, khối nhận năng lực mặc định: câu luyện tập theo mã đã gắn cho câu (đọc bảng, biểu đồ, bản đồ -> TIM_HIEU, còn lại NHAN_THUC), mở đầu và hình thành -> NHAN_THUC, vận dụng -> VAN_DUNG; `objectiveId` là mục tiêu cùng mã năng lực.
- `LessonOut.teachDate` (ngày dạy đầu tiên từ giáo án) và `AssignmentCreate.teachDate`: khi không gửi `dueAt`, hạn nộp = 23:59 ngày trước `teachDate` (giờ Việt Nam); thiếu cả hai: 422 `DUE_REQUIRED`.
- `GET /v1/lesson-plans`, `GET /v1/lesson-plans/{id}`: tiêu đề, tiết PPCT, tuần, ngày dạy, `suggestedDueAt` (23:59 ngày trước ngày dạy, giờ Việt Nam; null nếu giáo án không ghi ngày dạy), `activities` (4 hoạt động nhận ra được), mục tiêu kèm mã năng lực, các phần theo hoạt động, câu trắc nghiệm (`correctOption`, `answerSource` underline|docx_underline|teacher, `needsConfirmation`).
- `PUT /v1/lesson-plans/{id}/mcqs/{mcqId}/answer` `{correctOption}`: giáo viên chọn đáp án (nguồn `teacher`). 422 `INVALID_OPTION`.
- `POST /v1/lesson-plans/{id}/lesson`: tạo bản nháp bài chuẩn bị (câu khơi gợi, tối đa 2 thẻ đọc và 1 flashcard trích nguyên văn khung kiến thức, tối đa 5 câu luyện tập đã có đáp án kèm lời giải mẫu, 1 nhiệm vụ vận dụng). Khối đi qua VAL-01..10, không có khối nào được duyệt hay xuất bản. Câu chưa có đáp án bị bỏ (`skippedUnconfirmed`). 409 `LESSON_EXISTS`.

## 17. Bảng insight v2 (chỉ thêm, giáo viên của lớp)

- `GET .../insights` thêm trên mỗi câu: `topWrongOption` + `topWrongShare` (phương án sai được chọn nhiều nhất, tỉ lệ trên số em đã làm), `maxHintLevel` (bậc gợi ý cao nhất đã dùng), `needsReteach` (hơn 30% số em đã làm sai, tối thiểu 3 em, hoặc hơn 30% số em đã hỏi về câu đó), `questions` (2 chủ đề câu hỏi hay gặp, 2 ví dụ ẩn danh mỗi chủ đề). Ở mức bài: `blockedReasons` (số lần HABIT AI từ chối theo lý do, chỉ đếm), `reteachItemIds`.
- `POST .../insights/reteach` (tác giả bài): trích tối đa 3 đoạn nguồn đã duyệt đứng sau các câu cần dạy lại vào một bản NHÁP (tạo bản mới nếu bản hiện tại đã xuất bản), chạy VAL-01..10, không duyệt hay xuất bản gì. 409 `NOTHING_TO_RETEACH`, hoặc `DRAFT_EXISTS` từ bước tạo bản mới. Giao diện nối thêm `generate` (chế độ append) để có 2 đến 3 câu luyện thêm, vẫn là AI_PROPOSED chờ duyệt.
- `POST .../insights/analyze` có thêm `generatedBy: "replay"`: khi `DEMO_REPLAY=true` trả bản ghi sẵn (`app/insights/replay.json`), không gọi mạng; giao diện ghi rõ "bản ghi sẵn".
- Heatmap: mỗi câu có `competencyCode` (từ khối đã xuất bản), `competencies[]` ở mức bài cho tỉ lệ đúng lần đầu theo năng lực (gộp theo số lượt trả lời). Giao diện vẽ lưới câu x năng lực, đọc được trên 390.
- `POST .../insights/reteach` là idempotent: đoạn nguồn đã có khối `remediationDraft` chưa xử lý (chưa duyệt, chưa từ chối) trong bản nháp hiện tại thì không thêm lại; trả `alreadyExists=true`, `blocks=0` và `revisionId` của bản nháp đó để mở. Khối thêm mang `remediationDraft=true` (cột `content_block.remediation_draft`, migration 0009), hiện nhãn "Bản nháp dạy lại" ở hàng duyệt cho tới khi được duyệt.
- Không có bảng xếp hạng hay so sánh học sinh; mọi số liệu theo câu hoặc theo cả lớp (TT22).
