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
3. Học sinh **không bao giờ** thấy provenance/review/validation/đáp án/giải thích trước khi nộp câu đó (server đã lọc, FE đừng cố gọi).
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
- `GET /classes/{id}/assignments/{aid}/progress`: chỉ giáo viên của lớp đó, chỉ số tổng hợp (không có tên/đáp án từng học sinh).
- Chưa làm: thẻ ghi nhớ (flashcard) chưa có luồng trả lời riêng.
