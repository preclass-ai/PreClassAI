# Quyết định của agent (vấn đề · lựa chọn · lý do)

- `.claude/settings.json` (D-001 §5.2: acceptEdits, bỏ python/pip, deny docker down -v) **chưa áp**: bị classifier chặn vì tự sửa quyền của agent. Khải áp tay.
- `.env.*.example` trong `infra/` được thêm ngoại lệ `!.env.*.example` vào `.gitignore` để commit được.
- **Khóa revision khi PUBLISHED/SUPERSEDED, không phải khi khác DRAFT** (D-001 #5 nói "khác DRAFT"): trigger chặn sửa block/link/lesson_source chỉ khi revision đã PUBLISHED/SUPERSEDED; IN_REVIEW vẫn cho đổi `review_status` (duyệt diễn ra ở trạng thái này). Chặn sửa nội dung khi IN_REVIEW để ở tầng service. Lý do: nếu khóa cả IN_REVIEW thì không thể duyệt.
- **Migration 0001 dùng DDL đóng băng** (`0001_schema.sql` sinh từ models một lần) + `0001_triggers.sql`, tách lệnh bằng dòng đánh dấu vì asyncpg không chạy nhiều câu một lần. Migration sau viết tay. Lý do: `create_all` trong migration sẽ trôi theo models.
- **Trigger bắt `APPROVED` ⇔ review_event mới nhất là APPROVE khớp hash**; `review_event.created_at` dùng `clock_timestamp()` để thứ tự chặt trong cùng transaction.
- **Hai role DB tạo `NOLOGIN` trong migration**; vận hành đặt mật khẩu/LOGIN. Dev dùng superuser `preclass` của container (trigger vẫn áp dụng).
- **Block trả phẳng** (`parentId`+`position`), không lồng cây: tránh schema đệ quy trong OpenAPI. Payload block camelCase (`itemType`), khác snake_case trong đặc tả.
- **Upload DOCX tách endpoint** `/sources/docx`, `/sources/{id}/revisions/docx` (một path không khai báo được JSON và multipart). Bỏ `/auth/refresh` (cookie session). Thêm `GET /classes/{id}/assignments`, `GET /admin/audit-logs`. List có envelope `{items,nextCursor}` (cursor chưa dùng) để thêm phân trang không phá hợp đồng.
- **Không khai báo `security` toàn cục trong OpenAPI** (chỉ `securitySchemes`): Prism sẽ đòi cookie HttpOnly mà trình duyệt không đặt được. Route nào cần phiên ghi ở mô tả + API_GUIDE.
- **Tải bản nguồn mới không tự REVIEW_AGAIN bài** (D-001 #7): bài chỉ có `newerSourceAvailable`; AT-08 được kiểm ở `PUT /revisions/{id}/sources`.
- **Ruff `line-length=120`, E501/S608/S603 nới cho test/seed** để giữ SQL dễ đọc.

## Review Khải 14/11 — accepted
- **accepted:** cookie session (không refresh); tách upload DOCX; 3 endpoint thêm (`PUT /revisions/{id}/sources`, `GET /classes/{id}/assignments`, `GET /admin/audit-logs`); block trả phẳng; khóa revision khi PUBLISHED/SUPERSEDED. Điều kiện kèm theo: (a) sửa block ở IN_REVIEW phải đổi `content_hash` → mất approval (trigger `APPROVAL_INVALID` đã ép; service PATCH làm ở GĐ6); (b) publish kiểm `version` (GĐ8).
- **PUT sources (AT-08):** một transaction; mọi block có link tới anchor revision cũ, block phụ thuộc (bắc cầu) và cha trực tiếp → REVIEW_AGAIN (kể cả khi đang APPROVED/FLAGGED/REJECTED), ghi `SOURCE_REPLACED`; link đổi sang anchor trùng `excerpt_hash` ở bản mới (VERIFIED) hoặc UNRESOLVED. Không ghép theo locator khi nội dung đổi (tránh gán nhầm).
- **Rate limit đăng nhập trong bộ nhớ:** chấp nhận cho P0; bắt buộc chạy uvicorn `--workers 1` (ghi ở RUNBOOK).
- **Seed từ chối chạy khi `APP_ENV=production`;** mật khẩu `preclass-demo` chỉ có trong seed dev.
- **Test DB:** 127.0.0.1 thay `localhost` (resolve IPv6 trên Windows mất ~2 s mỗi kết nối); migrate+seed 1 lần mỗi session, mỗi test chạy trong transaction + SAVEPOINT rồi rollback. Full pytest ~23 s.
- **GĐ6 sửa block:** AUTO_CHECKED/FLAGGED sau khi sửa → UNREVIEWED (kết quả cũ thuộc hash cũ; GĐ7 chạy lại validation). Thêm block con vào cha đã APPROVED → cha REVIEW_AGAIN. Xóa block = xóa mềm kèm con, block phụ thuộc/cha đã APPROVED → REVIEW_AGAIN. Payload nhận lại cả khóa null (client gửi lại nguyên response) và từ chối khóa lạ.
