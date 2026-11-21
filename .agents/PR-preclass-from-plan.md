# PR D2: kiểm tra giáo án và tạo bài chuẩn bị (feat/preclass-from-plan)

Xếp chồng trên PR D1 (feat/lesson-plan-5512): merge D1 trước. Migration 0008 (chỉ thêm).

## Làm gì
- API `lesson-plans` (xem API_GUIDE 16): nạp, liệt kê, xem, giáo viên chọn đáp án, tạo bài nháp. Chỉ chủ giáo án (người khác 404).
- **Đọc giáo án là job nền**: POST trả 202 + jobId ngay; tiến trình con (RAM và 120 s như cũ); trạng thái queued/parsing (trang x/y)/done/failed; một job mỗi giáo viên (409 `PARSE_BUSY`); job nằm trong DB nên tải lại trang vẫn tiếp tục và tự sang màn Kiểm tra khi xong; lỗi có câu thân thiện.
- **Mã năng lực trên khối**: `content_block.competency_code` + `objective_id`, `extracted_mcq.competency_code`, `lesson.teach_date`. Mặc định theo hoạt động (hình thành và mở đầu NHAN_THUC, câu đọc bảng/biểu đồ TIM_HIEU, vận dụng VAN_DUNG); giáo viên sửa ở màn Kiểm tra (từng câu) và ở editor (Source Inspector). Là metadata, không đổi hash nên không reset duyệt.
- **Hạn nộp**: form giao bài nhận `teachDate`; bài tạo từ giáo án có ngày dạy thì ô ngày học và hạn nộp (23:59 ngày trước) tự điền; không có ngày dạy thì ô trống.
- Màn "Giáo án": tiến trình đọc, mục tiêu kèm năng lực, 4 hoạt động, câu trắc nghiệm (gạch chân hoặc cần xác nhận), chọn năng lực, nút "Tạo bài chuẩn bị trước giờ học".
- Bài nháp đi qua VAL-01..10; không có khối nào APPROVED.

## Đo thời gian đọc (Docker, giới hạn CPU, 512 MB, tệp thật 25 đến 42 trang; chỉ số, không nội dung)
Xem báo cáo cuối: số liệu ở mục "Hiệu năng" của handoff `.agents/handoffs/T19-lesson-plan-5512.md`.

## Chưa làm
Ảnh trang PDF tô vùng, hint bậc 1 đến 2 duyệt sẵn, câu ôn post_spaced (P2, sau thi).
