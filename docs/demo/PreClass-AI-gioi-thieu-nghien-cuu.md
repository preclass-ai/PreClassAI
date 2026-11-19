# PreClass AI — Truy vết từ nguồn đến học liệu: một thiết kế cho AI trong dạy học Địa lí

> **Bản demo:** https://pre-class-ai.vercel.app · **Tài liệu API:** https://pre-class-ai.vercel.app/docs
> Môn Địa lí 10–11 · Dữ liệu trong bản demo là **DỮ LIỆU MINH HỌA** (số liệu giả, không phải số liệu chính thức, không có dữ liệu học sinh thật).

---

## 1. Tóm tắt

Các công cụ AI soạn bài thường cho ra học liệu trôi chảy nhưng khó kiểm chứng: giáo viên không biết câu nào dựa vào đâu, con số nào từ đâu ra. PreClass AI thử nghiệm một hướng khác: **mọi khối học liệu do AI soạn đều phải gắn với đoạn nguồn gốc cụ thể (anchor), được máy kiểm tra bằng quy tắc xác định, và chỉ đến học sinh sau khi giáo viên duyệt từng khối**. Hệ thống không cho phép "duyệt tất cả", và nội dung đã xuất bản là bản chụp bất biến.

**Câu hỏi nghiên cứu.** Có thể thiết kế quy trình để AI hỗ trợ soạn học liệu Địa lí mà vẫn giữ được ba tính chất: (1) *truy vết được* nguồn của từng khối, (2) *kiểm chứng được* tính nhất quán số liệu và nguyên văn bằng cách xác định, và (3) *trách nhiệm của giáo viên* được ghi lại và gắn với đúng phiên bản nội dung đã duyệt?

## 2. Cơ sở và động cơ

- **Ảo giác và số liệu bịa** của mô hình ngôn ngữ đặc biệt nguy hiểm với Địa lí (số dân, sản lượng, tỉ lệ).
- **Duyệt nhưng không biết duyệt cái gì:** nếu giáo viên duyệt một văn bản đã bị sửa sau đó, sự duyệt mất ý nghĩa. Cần liên kết *quyết định duyệt* với *bản băm của nội dung*.
- **Học sinh cần tự làm trước, xem lời giải sau:** thiết kế đánh giá hình thành phải ép được thứ tự này ở phía máy chủ, không dựa vào giao diện.

## 3. Phương pháp: chuỗi "nguồn → khối → duyệt → xuất bản → giao → làm bài"

1. **Nguồn bất biến.** Giáo viên dán văn bản hoặc tải DOCX; hệ thống tách thành *anchor* (đoạn, tiêu đề, ô bảng), mỗi anchor có mã và hàm băm. Bản nguồn đã tải lên không bị sửa; sửa nguồn tạo phiên bản mới.
2. **Sinh học liệu (job bất đồng bộ).** Nhà cung cấp LLM chỉ trả về *bí danh* anchor; máy chủ ánh xạ lại về anchor thật và **không bao giờ tự duyệt**. Bản demo dùng nhà cung cấp mô phỏng (`mock`) để kết quả lặp lại được.
3. **Kiểm tra bằng quy tắc (VAL-01..09).**

   | Quy tắc | Kiểm tra | Mức |
   |---|---|---|
   | VAL-01 | anchor tồn tại và thuộc đúng bản nguồn của bài | Chặn |
   | VAL-02 | khối nguyên văn khớp đúng văn bản anchor (chuẩn hóa Unicode, giữ dấu tiếng Việt) | Chặn |
   | VAL-03 | khối nêu sự kiện phải có liên kết đã xác minh hoặc lý do không có nguồn; số trong nội dung phải có trong anchor liên kết | Chặn |
   | VAL-04 | câu hỏi trắc nghiệm có đúng 1 đáp án; đáp án trỏ tới lựa chọn có thật; đáp số có đơn vị | Chặn |
   | VAL-05 | nhãn lựa chọn A–D không trùng/thiếu | Cảnh báo/Chặn |
   | VAL-06 | khối đã duyệt nhưng băm nội dung hoặc băm nguồn đã đổi | Chặn |
   | VAL-08 | thuật ngữ nghi vấn theo bảng thuật ngữ địa lí | Cảnh báo |
   | VAL-09 | nguồn dùng chung trong trường phải ghi giấy phép/nguồn gốc | Chặn |

   Số dẫn xuất (tổng, hiệu, tỉ lệ, phần trăm) được **tính lại bằng số thập phân chính xác** và đối chiếu với đáp số trong nội dung.
4. **Duyệt từng khối, gắn băm.** Mỗi quyết định duyệt mang `contentHash` của khối như hiển thị; nếu nội dung đã đổi, hệ thống trả `409 STALE_REVIEW`. Sửa một khối làm mất hiệu lực các khối phụ thuộc. Giao diện không có "duyệt tất cả".
5. **Cổng xuất bản.** Chỉ cho xuất bản khi mọi khối đã duyệt hợp lệ, không còn lỗi chặn, nguồn còn hợp lệ, có ít nhất một câu hỏi và giáo viên xác nhận đã đọc. Kết quả là **bản chụp bất biến** (snapshot).
6. **Giao bài và làm bài.** Học sinh chỉ nhận dữ liệu đã lọc: *không có* đáp án, giải thích, nguồn, trạng thái duyệt trước khi nộp câu đó. Giải thích chỉ trả về sau khi nộp. Thu hồi một bản đã giao trả `410 WITHDRAWN` cho học sinh.

## 4. Kiến trúc và các bất biến được bảo đảm

| Lớp | Công nghệ | Ghi chú |
|---|---|---|
| Giao diện | Next.js (React, client app), Vercel | Cùng một origin với API qua rewrite `/v1` |
| API | FastAPI (Python 3.12), Render | Hợp đồng OpenAPI sinh từ Pydantic; JSON camelCase; lỗi RFC 9457 |
| Cơ sở dữ liệu | PostgreSQL 16, Neon | Bất biến ép **ngay trong CSDL** (trigger) |

- **Bất biến ở tầng CSDL, không chỉ ở mã Python:** bảng sự kiện/kiểm toán/lần làm bài chỉ thêm (append-only); bản nguồn, anchor và bản chụp đã xuất bản không sửa được; chuyển trạng thái bản bài học được kiểm soát bằng trigger.
- **Khóa lạc quan:** sửa khối phải kèm `version` (xung đột → `409 VERSION_CONFLICT`).
- **Bảo mật:** cookie phiên `Secure; HttpOnly; SameSite=Lax`, header CSRF bắt buộc với yêu cầu ghi, tài nguyên của người khác trả `404` (không lộ sự tồn tại), học sinh gọi API nguồn gốc cũng nhận `404`, giới hạn thử đăng nhập theo IP của người dùng (đã cấu hình đọc IP thật qua proxy; chưa kiểm chứng riêng trên cloud).
- **Truy vết trách nhiệm:** nhật ký kiểm toán ghi cả lượt xem nguồn của giáo viên (không ghi nội dung).

## 5. Kết quả kiểm chứng đã thực hiện

Các số liệu dưới đây lấy từ lần chạy thực tế trên bản cloud và bộ kiểm thử trong kho mã (không phải ước lượng).

| Hạng mục | Kết quả |
|---|---|
| Kiểm thử backend (pytest, CSDL Postgres thật) | 167 đạt, 1 bỏ qua; ruff và mypy `--strict` sạch |
| Kiểm thử frontend (Vitest) | 33 đạt; lint, kiểm tra kiểu sạch |
| Smoke toàn luồng qua URL cloud | **Đạt**: nguồn → soạn → duyệt từng khối → xuất bản → giao → học sinh làm → thu hồi → `410` |
| Học sinh gọi API nguồn gốc | `404` (đã kiểm chứng trên 390, 768 và WebKit; có thêm test tự động ở backend) |
| Cookie phiên trên Chromium | `Secure`, `HttpOnly`, `SameSite=Lax` |
| Lỗi máy chủ 5xx / giới hạn 429 / thiếu CSRF trong luồng e2e (project 390 và WebKit) | 0 / 0 / 0 |
| Lỗi console ngoài 401 `/v1/me` trước khi đăng nhập (390, WebKit) | 0 |
| Thời gian tải trang danh sách bài (1280 px, lần đo) | 476 ms |
| Bộ e2e (Playwright): 390, 768, 1280 px và WebKit (mô phỏng Safari iPhone) | GV S01→S06 đạt trên 390, 768 và WebKit; ở 1280 bước S01 chập chờn do lỗi hiển thị cũ ở mục dưới (đã sửa gốc, chờ chạy lại sau khi triển khai) |

Hai lỗi thật tìm thấy **chỉ nhờ chạy trên môi trường triển khai thật** (và đã được sửa):
1. *Hiển thị cũ:* danh sách nguồn không có dòng mới sau khi lưu nếu lần tải đầu còn đang chạy khi thao tác ghi hoàn tất (React Query gộp lần làm mới vào yêu cầu cũ). Sửa gốc bằng "hủy rồi làm mới", có test tái hiện cả lỗi lẫn bản sửa.
2. *Cấu hình:* biến `API_ORIGIN` thiếu khi build làm Vercel trỏ vào địa chỉ nội bộ. Nay build **thất bại có thông báo rõ** thay vì triển khai hỏng, và API từ chối khởi động nếu `FRONTEND_ORIGIN` không phải https công khai.

## 6. Giới hạn và mối đe dọa với tính hợp lệ

- **Nhà cung cấp LLM là mô phỏng.** Kết quả demo chứng minh *cơ chế truy vết và kiểm tra*, **không** chứng minh chất lượng nội dung của mô hình thật. Đánh giá độ chính xác thực của LLM cần một thực nghiệm riêng.
- **Quy tắc kiểm tra mang tính hình thức.** VAL-02/03 bảo đảm khớp văn bản và số liệu, không bảo đảm lập luận sư phạm đúng; vai trò phán đoán vẫn thuộc giáo viên.
- **Quy mô và dữ liệu nhỏ:** 6 bài minh họa, số liệu giả; chưa có đánh giá với học sinh thật.
- **Hạ tầng miễn phí:** máy chủ API ngủ sau 15 phút không dùng (lần gọi đầu có thể chậm 30–60 giây), giới hạn bộ nhớ 512 MB, CSDL tự tạm dừng khi rảnh; giới hạn đăng nhập lưu trong bộ nhớ một tiến trình.
- **Chưa làm:** ảnh/bản đồ do AI sinh (VAL-07 là chỗ giữ chỗ), kiểm thử tải nặng, đánh giá khả dụng với người dùng thật.
- **Đạo đức và dữ liệu:** bản cloud chỉ chứa dữ liệu minh họa; triển khai với dữ liệu học sinh thật sẽ chạy trên máy chủ trong nước.

## 7. Hướng dẫn trải nghiệm (5 phút)

> Mở link **trước 1 phút** để đánh thức máy chủ. Mật khẩu của mọi tài khoản demo: `preclass-demo`.

1. Đăng nhập giáo viên → **Nguồn** → *Thêm nguồn* (dán một đoạn văn kèm bảng số liệu) → *Lưu nguồn*; nguồn mới hiện ngay ở đầu danh sách.
2. **Bài học** → *Tạo bài* → chọn nguồn → hệ thống soạn học liệu (mô phỏng). Mở một khối, xem **Bằng chứng từ nguồn** và kết quả kiểm tra VAL.
3. Tab **Duyệt**: duyệt từng khối (thử sửa một khối rồi quan sát việc duyệt cũ mất hiệu lực).
4. Tab **Xuất bản & giao bài**: xem bảng kiểm tra trước khi xuất bản, xuất bản, giao cho lớp 10A1.
5. Đăng xuất, đăng nhập học sinh: làm 2 câu, chỉ sau khi nộp mới thấy giải thích. Thử thu hồi bài ở tài khoản giáo viên và tải lại phía học sinh (thấy thông báo đã thu hồi).
6. Mở **/docs** để xem hợp đồng API đầy đủ.

## 8. Tài khoản demo

**Giáo viên (20 tài khoản mới + 2 tài khoản gốc)** — đăng nhập bằng email:

| Tài khoản | Ghi chú |
|---|---|
| `gv01@preclass.local` … `gv20@preclass.local` | Mỗi tài khoản có không gian riêng (bắt đầu trống); dùng nguồn "Phân bố dân cư theo vùng" (dùng chung toàn trường) hoặc tự thêm nguồn. Thuộc cả hai lớp demo nên giao bài được |
| `gv.dia@preclass.local` | Có sẵn 6 bài minh họa (đã xuất bản và giao cho 10A1) |
| `gv.khac@preclass.local` | Giáo viên thứ hai, thấy bài riêng của mình (kiểm tra cách ly dữ liệu giữa giáo viên) |

**Học sinh (20 tài khoản mới + 30 tài khoản gốc)** — đăng nhập bằng mã học sinh:

| Mã | Lớp |
|---|---|
| `HS10-16` … `HS10-35` | 10A1 (mới, chưa dùng) |
| `HS10-01` … `HS10-15` | 10A1 (HS10-12 đến HS10-15 đã bị kiểm thử tự động sử dụng nên đã có bài làm) |
| `HS11-01` … `HS11-15` | 11A1 |

Quản trị (xem nhật ký kiểm toán): `admin@preclass.local`.

> Các tài khoản mới (`gv01`–`gv20`, `HS10-16`–`HS10-35`) được tạo tự động mỗi lần API khởi động (idempotent) sau khi bản mã chứa chúng được triển khai.
> Mật khẩu chung chỉ dành cho bản demo công khai; không dùng cho dữ liệu thật.

## 9. Khả năng tái lập

- Mã nguồn: kho `preclass-ai/PreClassAI` (backend `apps/api`, frontend `apps/web`, hợp đồng `apps/api/openapi/openapi.json`).
- Kiến trúc và quyết định: `docs/adr/ADR-0010-fastapi-backend.md`, `docs/adr/ADR-0011-cloud-demo-deploy.md`.
- Triển khai và khôi phục: `docs/operations/DEPLOY-cloud.md`; đặt lại CSDL demo: `scripts/ops/reset_demo_db.py`.
- Chạy kiểm thử toàn luồng: `python scripts/smoke.py --base https://pre-class-ai.vercel.app`.

## 10. Hướng nghiên cứu tiếp theo

1. Thực nghiệm so sánh mô hình LLM thật: tỉ lệ khối bị chặn bởi VAL-01..04, tỉ lệ giáo viên sửa hoặc từ chối, thời gian duyệt mỗi khối.
2. Đo tác động lên học sinh: tỉ lệ đúng trước/sau khi xem giải thích, tính thích hợp của lời giải thích đã được duyệt.
3. Mở rộng truy vết sang ảnh, bản đồ và biểu đồ (VAL-07).
4. Triển khai trong nước với dữ liệu thật theo quy định bảo vệ dữ liệu cá nhân, sau khi có đánh giá bảo mật độc lập.
