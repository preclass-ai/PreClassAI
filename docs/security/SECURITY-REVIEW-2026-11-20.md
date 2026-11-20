# Rà soát bảo mật trước khi phát link khảo sát — 2026-11-20

Phạm vi: bản demo trên cloud (Vercel + Render + Neon), dữ liệu minh họa và khách ẩn danh. Nhánh `sec/prelaunch`.
Mức tin cậy: tự rà soát bằng mã, test tự động và công cụ quét; **chưa có kiểm thử xâm nhập độc lập**.

## OWASP Top 10 (2021)

| # | Hạng mục | Đã có | Đã sửa trong đợt này | Tồn đọng |
|---|---|---|---|---|
| A01 | Kiểm soát truy cập | Vai trò ở máy chủ (`require_role`); tài nguyên của người khác trả `404`; HS không thấy provenance/đáp án trước khi nộp (PR-08); khách là HS nên route GV/admin trả 403; test IDOR cho bài, khối, nguồn, lớp | `/docs` và `/v1/openapi.json` điều khiển bằng `DOCS_ACCESS` (`staff`/`off`); thống kê khách chỉ ADMIN; thao tác admin có audit | Test IDOR chưa phủ mọi route |
| A02 | Lỗi mã hóa | HTTPS (Vercel, Render); cookie `Secure; HttpOnly; SameSite=Lax`; mật khẩu argon2; token phiên lưu dạng băm; Neon `ssl=require` | HSTS `max-age=31536000; includeSubDomains` | Chưa bật HSTS preload |
| A03 | Injection | SQLAlchemy tham số hóa; React thoát ký tự (không có `dangerouslySetInnerHTML`, không render HTML/markdown từ payload); xuất CSV chống công thức (`=`, `+`, `-`, `@`) | Test XSS `<img src=x onerror=…>` trong khối và trích đoạn nguồn (vitest) và thăm dò trong luồng e2e (`window.__xss` phải không tồn tại); CSP; href phiếu khảo sát chỉ nhận `https://` | CSP `script-src` còn `'unsafe-inline'` (xem dưới) |
| A04 | Thiết kế không an toàn | Bất biến ở CSDL (trigger: chỉ-thêm, snapshot bất biến); duyệt gắn băm nội dung; giới hạn khách theo IP và tổng | Tham số hóa `GUEST_CREATE_PER_HOUR`, `GUEST_MAX_ACTIVE`, cảnh báo ≥ 80% | Bộ đếm giới hạn nằm trong bộ nhớ một tiến trình (mất khi khởi động lại); chưa có CAPTCHA khi tạo khách |
| A05 | Cấu hình sai | Guard `API_ORIGIN` (build lỗi nếu thiếu/riêng tư); `FRONTEND_ORIGIN` phải https công khai khi `demo`/`production`; seed từ chối `production` | **Mật khẩu seed không còn mặc định trên cloud** (`SEED_*_PASSWORD` ≥ 12 ký tự, thiếu thì không tạo tài khoản nhưng không sập); header: CSP, HSTS, nosniff, Referrer-Policy, Permissions-Policy; API: nosniff + `no-store` cho dữ liệu người dùng | Cấu hình trên dashboard Render/Vercel/Neon nằm ngoài mã (phải kiểm tay) |
| A06 | Thành phần lỗi thời | Khóa phiên bản (`uv.lock`, `pnpm-lock.yaml`) | `pip-audit` (không có lỗ hổng đã biết); `pnpm audit --prod` có 4 cảnh báo `postcss` (2 high, 2 moderate, kéo vào qua `next`, chỉ chạy lúc build) → ép `postcss ^8.5.23` bằng `pnpm.overrides`, audit còn 0 | Next 15.x và phụ thuộc Python (`>=`) cần cập nhật định kỳ |
| A07 | Xác thực | Giới hạn thử đăng nhập; phiên 8 giờ (khách 14 ngày); đăng xuất thu hồi phiên; CSRF bằng header + kiểm Origin | ADMIN khóa sau **3** lần sai / 15 phút; `rotate_passwords.py` (thu hồi phiên); HS seed không đăng nhập bằng mật khẩu (tùy chọn) | Không có MFA cho admin; 22 tài khoản GV dùng chung một mật khẩu seed |
| A08 | Toàn vẹn phần mềm và dữ liệu | Lockfile; CI kiểm `openapi.json` và `schema.d.ts` khớp mã; snapshot xuất bản bất biến | — | Trang `/docs` nạp Scalar từ CDN jsdelivr (đã khóa phiên bản, chưa có SRI) |
| A09 | Ghi log và giám sát | Bảng `audit_log` (đăng nhập, xem nguồn, duyệt, xuất bản…); log từ chối CSRF (không có cookie/token) | Audit thao tác admin; cảnh báo ngưỡng khách (chỉ số đếm, không IP/mã); UptimeRobot theo dõi sống/chết | Chưa có cảnh báo chủ động qua email/chat ngoài UptimeRobot; log Render lưu ngắn |
| A10 | SSRF | API không nhận URL từ người dùng để tải về; DOCX liên kết ngoài bị từ chối, không bao giờ được tải | — | Nhà cung cấp LLM `openai_compatible` lấy URL từ biến môi trường (hiện dùng `mock`) |

Đã làm thêm ở lớp tệp tải lên (A04/A05): DOCX ≤ 10 MB, ≤ 20 MB sau giải nén, ≤ 1000 thành phần, tỉ lệ nén ≤ 100:1 (chống zip bomb), từ chối macro, đối tượng nhúng và nội dung ngoài. Có test.

### Về CSP
`script-src 'self' 'unsafe-inline'`, không `'unsafe-eval'` ở production. Dùng nonce cần biến mọi trang tĩnh thành trang động và đổi cách Vercel phục vụ; chưa làm trước buổi khảo sát. Mức rủi ro thực tế thấp vì ứng dụng không render HTML từ dữ liệu người dùng (xem A03). Việc tiếp: chuyển sang nonce/hash khi có thời gian. `/docs` (trang Scalar của API) không áp CSP vì nạp script từ CDN.
Header của Next không áp lên các đường `/v1/*` được chuyển tiếp tới API; phản hồi JSON của API có `nosniff` và `no-store` riêng.

## Dữ liệu khảo sát

| Mục | Nội dung |
|---|---|
| Danh tính thu thập | **Chỉ mã khảo sát `KS-XXXX`** (ngẫu nhiên, không chứa thông tin cá nhân). Không tên, email, mật khẩu, số điện thoại. IP không bao giờ ghi vào CSDL: chỉ dùng trong bộ nhớ để giới hạn tốc độ |
| Dữ liệu làm bài | Mỗi lần trả lời: câu hỏi, đáp án chọn/nhập, đúng/sai, thời điểm. **Lưu ý:** câu trả lời dạng văn bản tự do do học sinh nhập có thể chứa thông tin cá nhân nếu em tự viết vào; thông báo trước khi vào chỉ nói không thu tên/email |
| Thông báo cho người tham gia | Hiện trước khi vào: "Không thu tên hay email. Kết quả làm bài chỉ dùng cho nghiên cứu và không gắn với danh tính của em." |
| Nơi lưu | PostgreSQL trên Neon, vùng AWS Singapore. Nhà cung cấp hạ tầng (Vercel, Render, Cloudflare) có thể ghi log IP theo chính sách của họ, ngoài kiểm soát của ứng dụng |
| Xuất dữ liệu | `GET /v1/admin/survey/export.csv` (ADMIN/GV, có audit): `survey_code, lesson, item, first_attempt_is_correct, answered_at_utc`. Không cột định danh nào khác |
| Thời hạn lưu | **Đề xuất:** giữ đến hết đợt khảo sát cộng 90 ngày để nhóm nghiên cứu phân tích, sau đó xóa. Nhóm nghiên cứu cần chốt con số này |
| Cách xóa | (1) `scripts/ops/purge_guests.py --dry-run` rồi chạy thật: khách **chưa làm bài** bị xóa hẳn. (2) Khách **đã có bài làm** chỉ bị vô hiệu hóa (không đăng nhập/quay lại được), vì bảng lần làm bài là chỉ-thêm ở mức CSDL. (3) Xóa hoàn toàn dữ liệu làm bài: `scripts/ops/reset_demo_db.py` (xóa cả dữ liệu minh họa) hoặc xóa branch/dự án trên Neon. Không có nút xóa theo mã khảo sát riêng lẻ |
| Quyền truy cập | Chỉ ADMIN/GV đăng nhập; mật khẩu lấy từ biến môi trường, đổi bằng `rotate_passwords.py` |

## Việc phải làm trên dashboard (ngoài mã)
- Render: đặt `SEED_TEACHER_PASSWORD`, `SEED_REVIEWER_PASSWORD`, `SEED_ADMIN_PASSWORD` (≥ 12 ký tự), `DOCS_ACCESS=staff`; chạy `rotate_passwords.py` cho DB hiện có.
- Chốt thời hạn lưu dữ liệu khảo sát và ghi vào phiếu khảo sát.
