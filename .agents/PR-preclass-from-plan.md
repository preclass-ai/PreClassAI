# PR D2: kiểm tra giáo án và tạo bài chuẩn bị (feat/preclass-from-plan)

Xếp chồng trên PR D1 (feat/lesson-plan-5512): merge D1 trước. Không migration mới.

## Làm gì
- API `lesson-plans` (xem API_GUIDE 16): nạp, liệt kê, xem, giáo viên chọn đáp án, tạo bài nháp. Chỉ chủ giáo án (người khác 404).
- Màn "Giáo án" (`/plans`, `/plans/[planId]`): nạp tệp, hiện mục tiêu kèm năng lực, 4 hoạt động (xanh khi nhận ra, vàng khi chưa thấy), từng đoạn theo hoạt động, câu trắc nghiệm (nhãn "Từ gạch chân" hoặc vàng "Cần xác nhận", chọn đáp án 1 chạm), gợi ý hạn nộp, nút "Tạo bài chuẩn bị trước giờ học" sang trang soạn.
- Bài nháp đi qua VAL-01..10; không có khối nào APPROVED; cổng xuất bản vẫn bắt duyệt từng khối.

## Kiểm tra
Test tích hợp mới (5): nạp DOCX, đọc, xác nhận, tạo bài, 409 tạo lần hai, câu chưa xác nhận bị bỏ, PDF hai bài có thẻ kiến thức, IDOR (học sinh 403, giáo viên khác 404), tệp sai loại. Playwright `plans.spec.ts` 390, 768, 1280, WebKit: nạp, kiểm tra, xác nhận, tạo bài, sang trang soạn. Ảnh: `.agents/screens-plans/`.

## Chưa làm (so với yêu cầu)
Ảnh trang có tô vùng; job nền; gắn mã năng lực vào khối; hint bậc 1 đến 2 duyệt sẵn; câu ôn sau giờ (post_spaced); tự điền hạn nộp vào form giao bài (chỉ gợi ý ở màn kiểm tra, vì 24/25 bài thật không ghi ngày dạy).
