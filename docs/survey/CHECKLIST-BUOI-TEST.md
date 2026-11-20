# Checklist buổi test khảo sát PreClass AI

Link học sinh: https://pre-class-ai.vercel.app/thu?bai=dan-so-vung · QR: `docs/survey/qr-khao-sat.png` · Hướng dẫn cho học sinh: `docs/survey/HUONG-DAN-HOC-SINH.md`

## Trước buổi (T-1 ngày và T-5 phút)

- [ ] **T-1 ngày:** `curl https://pre-class-ai.vercel.app/v1/health` trả `{"status":"ok","commit":"…"}` và `commit` trùng 7 ký tự đầu của `git log origin/main -1` (hoặc commit bạn định chạy).
- [ ] **T-1 ngày:** `curl https://pre-class-ai.vercel.app/v1/auth/config` trả `{"guestEnabled":true}`.
- [ ] **T-1 ngày:** một khách thử (`/thu?bai=dan-so-vung`) chỉ thấy **1 bài** "Phân bố dân cư theo vùng" và nhận mã `KS-XXXX`.
- [ ] **T-5 phút:** mở link trên máy của bạn để đánh thức máy chủ (nếu trang hiện "Máy chủ đang khởi động", đợi 30–60 giây rồi bấm Thử lại).
- [ ] **T-5 phút:** UptimeRobot hiện **Up** (monitor `https://pre-class-ai.vercel.app/v1/health`, 5 phút/lần).
- [ ] **T-5 phút:** `https://pre-class-ai.vercel.app/v1/admin/survey/stats` (đăng nhập admin) cho thấy `activeGuests` và `maxActive` (mặc định 500) còn dư; `GUEST_CREATE_PER_HOUR` đủ cho cả lớp dùng chung một Wi-Fi (khuyến nghị `200`).
- [ ] Có sẵn phiếu khảo sát (link hoặc bản giấy) và nơi ghi mã `KS-XXXX`; nếu muốn nút "Mở phiếu khảo sát", đã đặt `NEXT_PUBLIC_SURVEY_URL` trên Vercel và Redeploy.
- [ ] QR chiếu lên màn hình hoặc in sẵn; kiểm bằng điện thoại thật rằng quét ra đúng link.
- [ ] **Không chạy E2E hay nhờ người khác thử trên bản thật trong giờ khảo sát** (mỗi thao tác làm bài của khách là một dòng dữ liệu nghiên cứu).

## Trong buổi

1. Học sinh **quét QR** (hoặc mở link) → trang tự vào bài.
2. **Ghi mã `KS-XXXX`** hiện ở đầu trang (nút Sao chép) vào phiếu.
3. **Làm từng câu**, bấm *Nộp câu trả lời*, đọc lời giải thích hiện ra sau khi nộp.
4. **Điền phiếu khảo sát** và nhập đúng mã KS.
5. Giáo viên đi quanh lớp; nhắc học sinh **không gõ tên, lớp, số điện thoại** vào ô trả lời tự do.

## Xử lý sự cố

| Hiện tượng | Cách xử lý |
|---|---|
| Trang trắng hoặc rất chậm | Tải lại trang (kéo xuống trên điện thoại); thử lại sau 10 giây |
| "Máy chủ đang khởi động" | Server ngủ: **chờ 60 giây**, bấm **Thử lại**; nếu cả lớp cùng gặp, mở link bằng một máy trước để đánh thức |
| "Vào làm thử" báo lỗi hoặc bị từ chối | Báo **giáo viên**; giáo viên kiểm `/v1/auth/config` và `/v1/admin/survey/stats`. Lỗi 429: quá nhiều khách tạo từ một Wi-Fi trong một giờ (tăng `GUEST_CREATE_PER_HOUR` trên Render); lỗi 503: chạm `GUEST_MAX_ACTIVE` |
| Học sinh đóng trang, mất phiên | Vào lại link → mục **Đã có mã khảo sát?** → nhập `KS-XXXX` → **Vào lại bằng mã** (sai 5 lần/15 phút sẽ bị khóa tạm) |
| Học sinh quên mã khảo sát | Nếu trang còn mở, mã ở đầu trang; nếu không thì làm lại bằng mã mới và ghi chú trên phiếu |
| Không có mạng ở một số máy | Đổi sang mạng di động; không cần cài gì |
| Toàn hệ thống không mở được | Kiểm `https://preclass-api.onrender.com/v1/health` và UptimeRobot; xem `docs/operations/RUNBOOK.md` mục "Cloud demo" |

## Sau buổi

- [ ] **Xuất CSV:** đăng nhập ADMIN hoặc GV, mở `https://pre-class-ai.vercel.app/v1/admin/survey/export.csv` (tải về `survey.csv`: `survey_code, lesson, item, first_attempt_is_correct, answered_at_utc`). Lưu bản sao ở nơi an toàn của nhóm nghiên cứu.
- [ ] **Ghi số học sinh tham gia:** `activeGuests` ở `/v1/admin/survey/stats`, hoặc số mã `KS-` khác nhau trong CSV. Ghi cả số phiếu đã thu.
- [ ] **Tắt khách nếu cần:** trên Render đặt `GUEST_ACCESS_ENABLED=false` rồi để dịch vụ khởi động lại (link `/thu` sẽ về trang đăng nhập); bật lại bằng `true`.
- [ ] Chốt **thời hạn lưu dữ liệu** (đề xuất: hết đợt khảo sát + 90 ngày), sau đó dọn bằng `scripts/ops/purge_guests.py --dry-run` rồi chạy thật (khách đã có bài làm chỉ bị vô hiệu hóa vì bảng bài làm là chỉ-thêm) hoặc reset DB demo.
- [ ] Nếu muốn dùng lại bản demo sạch cho lần sau: backup rồi reset theo `RUNBOOK.md`.
