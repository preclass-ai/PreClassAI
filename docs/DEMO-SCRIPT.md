# Kịch bản demo 7 đến 8 phút

Giáo án 5512 lấy từ máy của thầy (không nằm trong repo). Bản dự phòng cùng luồng: `apps/web/tests/e2e/fixtures/plan-mau.docx`.

| # | Màn và thao tác | Câu nói chính | Nếu trục trặc |
|---|---|---|---|
| 1 | **Giáo án** (`/plans`): chọn tệp, bấm "Đọc giáo án". Thanh "Đang đọc giáo án… trang x/y" chạy rồi tự sang màn Kiểm tra. (45 giây) | "Thầy không phải chờ. Trang đọc ở nền, tải lại trang vẫn còn." | Tải sẵn giáo án từ trước giờ thi; nếu báo bận, mở lại `/plans` để xem việc đang chạy. |
| 2 | **Kiểm tra bóc tách**: chỉ vào câu "Cần xác nhận", chọn đáp án, xem ô năng lực của từng câu. (1 phút) | "Đáp án chỉ lấy từ chỗ gạch chân hoặc thầy chọn. AI không đoán đáp án." | Dùng giáo án mẫu. |
| 3 | Bấm "Tạo bài chuẩn bị trước giờ học": vào bài ở tab Soạn. (30 giây) | "Mỗi khối đều có nguồn trong giáo án." | Mở bài đã tạo sẵn ở `/lessons`. |
| 4 | Tab **Xuất bản & giao bài**: duyệt từng khối, xuất bản, giao cho lớp. Hạn nộp tự điền là ngày học trừ 1 ngày, 23:59. (1 phút 30) | "Học sinh chỉ thấy nội dung đã duyệt. Hạn nộp lấy từ ngày dạy trong giáo án." | Bài đã xuất bản sẵn; chỉ cần giao bài. |
| 5 | **Học sinh khách** (`/thu`, mở trên điện thoại): làm câu 1, xin gợi ý 1 rồi 2, hỏi HABIT AI "Đáp án là gì" để thấy lời từ chối, nộp bài, bấm "Habit giải thích". (2 phút) | "HABIT AI không đưa đáp án trước khi em nộp. Sau khi nộp mới có lời giải đã duyệt." | `CHAT_MODE=rule` (4 nút gợi ý vẫn chạy, không cần mạng). |
| 6 | **Giáo viên, mục Lớp & bài giao**: mở bài giao, xem bản đồ nhiệt năng lực, "Học sinh hỏi gì", bấm "Đề xuất dạy lại". Bản nháp mở ra, nhãn "Bản nháp dạy lại". (1 phút 30) | "Thầy thấy chỗ cả lớp vướng, và bản nháp dạy lại vẫn phải được thầy duyệt." | `DEMO_REPLAY=true` cho phần "Học sinh hỏi gì" (có nhãn bản ghi sẵn). |
| 7 | **Dữ liệu của em đi đâu** (`/du-lieu`, link ở chân trang). (30 giây) | "Em biết mình bị thu gì, lưu ở đâu, bao lâu, và AI có nhận câu hỏi của em không." | Mở thẳng `/du-lieu`. |

## Trước giờ thi
- [ ] `GET /v1/health` trả đúng commit vừa deploy; `/v1/auth/config` đúng `chatMode`.
- [ ] UptimeRobot đang **Up**.
- [ ] Mở link demo và đăng nhập trước 10 phút để máy chủ không còn ngủ.
- [ ] Giáo án demo đã tải, trạng thái "xong"; bài chuẩn bị đã có.
- [ ] Tạo sẵn một mã khách để dự phòng; tắt thông báo điện thoại và máy tính.
- [ ] Biết cách đổi `CHAT_MODE=rule` (RUNBOOK, mục "Trước giờ thi").
