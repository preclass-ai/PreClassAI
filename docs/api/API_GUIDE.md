# API guide cho frontend (v0, gửi 14/11 · freeze v1 sáng 16/11)

Hợp đồng chính thức: [`apps/api/openapi/openapi.json`](../../apps/api/openapi/openapi.json) (sinh từ code, CI chặn lệch). Tài liệu này là hướng dẫn đọc nhanh. Mô hình dữ liệu: [`DATA_MODEL.md`](DATA_MODEL.md).

> **Trạng thái:** mọi endpoint đã có schema + ví dụ. **Đã chạy thật (GĐ4):** `POST /auth/login`, `POST /auth/logout`, `GET /me`, `GET /classes`, `GET /admin/audit-logs`. Các endpoint còn lại trả `501 NOT_IMPLEMENTED` cho tới các giai đoạn 5–9. **Hãy dựng FE trên Prism mock** (bên dưới). Sau freeze v1 chỉ *thêm* field, không đổi tên/xóa field. Mọi thay đổi hợp đồng báo Khải trước.

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
- Tải bản nguồn mới **không** tự đánh `REVIEW_AGAIN` cho bài: bài chỉ hiện `newerSourceAvailable=true` cho tới khi GV gọi `PUT /revisions/{id}/sources`.
- Chưa có cursor pagination (envelope `{items,nextCursor}` đã có sẵn).
- Payload trong block dùng camelCase (`itemType`, `rubricPoints`), khác snake_case ghi trong đặc tả.
