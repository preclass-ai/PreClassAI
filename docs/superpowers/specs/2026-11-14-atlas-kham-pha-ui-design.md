# Atlas khám phá — thiết kế lại giao diện PreClass AI

## Mục đích

PreClass AI phục vụ học sinh THPT học **Địa lí** và giáo viên tạo, kiểm chứng, giao bài. Giao diện hiện tại rõ chức năng nhưng thiên về bảng và thẻ xám. Bản thiết kế này tạo cảm giác khám phá, gần gũi và hiện đại trên toàn app, đồng thời giữ sự tin cậy của nội dung có nguồn.

## Hướng đã chọn

- **Atlas khám phá (đã chọn):** xanh biển và xanh lá làm nền nhận diện, vàng nắng làm điểm nhấn, đường đồng mức và tọa độ địa lí làm họa tiết nhẹ. Phù hợp cả bài tập học sinh lẫn công cụ giáo viên; không phụ thuộc ảnh lớn hay thư viện hiệu ứng.
- **Tạp chí Địa lí (đã cân nhắc):** ảnh phong cảnh lớn và bố cục biên tập. Tạo cảm xúc tốt nhưng tăng chi phí tải ảnh, khó giữ mật độ thông tin và tính nhất quán ở màn duyệt, biên tập.

## Phạm vi và giới hạn

- Làm mới toàn bộ giao diện ở mức ngang nhau: đăng nhập; danh sách và bài làm học sinh; nguồn, bài học, trình soạn, duyệt, xuất bản, lịch sử, lớp/tiến độ của giáo viên; nhật ký quản trị.
- Giữ Next.js, React Query, client OpenAPI và toàn bộ hợp đồng `/v1`; không đổi quyền, cách chấm, thời điểm hiện lời giải, hay nội dung dữ liệu mẫu.
- Dùng chữ **Địa lí** nhất quán. Dữ liệu minh họa vẫn phải có nhãn rõ. Không gắn phần thưởng, streak hay điểm số chưa có trong API.
- Không thêm bộ ảnh nặng hoặc thư viện animation. Họa tiết địa hình có thể tạo bằng CSS/SVG nhẹ và không chứa thông tin địa lí giả.

## Ngôn ngữ thị giác

- Nền sáng hơi xanh kem; bề mặt trắng ấm; chữ than đậm; xanh đại dương cho hành động chính, xanh lá cho trạng thái tích cực, vàng nắng cho điểm nhấn. Mỗi trạng thái vẫn có chữ và hình dạng, không dựa vào màu đơn thuần.
- Chữ dễ đọc trên màn 390 px, tiêu đề có cấp bậc rõ, số liệu và tiến độ nổi bật. Giữ khoảng trắng thoáng; thẻ bo vừa phải, viền mảnh, bóng nhẹ.
- Họa tiết đường đồng mức, vòng tọa độ, chấm định vị xuất hiện ở hero hoặc vùng trống, không phủ lên nội dung bài hay biểu mẫu.
- Dark mode có cùng phân cấp và độ tương phản; không chỉ đảo màu tự động.

## Bố cục theo luồng

- **Đăng nhập:** lời chào ngắn, nhận diện Địa lí rõ, biểu mẫu đặt trọng tâm; trên desktop có mảng minh họa atlas, trên mobile biểu mẫu lên trước.
- **Học sinh:** đầu trang chào và tóm tắt bài đang làm; thẻ bài giao nêu tiêu đề, lớp, hạn và tiến độ bằng cả số lẫn thanh. Trong bài, câu hỏi có nhịp đọc rõ, vùng chọn đáp án đủ lớn, kết quả và giải thích chỉ xuất hiện sau khi nộp như API quy định.
- **Giáo viên:** cùng hệ màu và thành phần; danh sách nguồn/bài có bộ lọc hoặc trạng thái dễ quét, màn soạn giữ inspector nổi bật nhưng không lấn nội dung, duyệt và publish gate thể hiện mức độ sẵn sàng bằng chữ và biểu tượng. Lịch sử và tiến độ ưu tiên số liệu có thể đọc nhanh.
- **Quản trị:** bảng nhật ký gọn, rõ ngày giờ/hành động, dùng cùng shell và trạng thái tải/lỗi/trống.
- Điều hướng desktop rõ nhóm việc; mobile không tràn ngang và vẫn thấy hành động chính. Giữ đường tắt bàn phím tới nội dung chính.

## Cảm giác tương tác

- Hover/focus/pressed phản hồi khoảng 120–220 ms; chỉ chuyển động opacity, transform nhẹ hoặc màu. Thanh tiến độ và trạng thái tải chuyển tiếp êm, không làm đổi bố cục đột ngột.
- Tôn trọng `prefers-reduced-motion`: tắt chuyển động trang trí và rút ngắn transition. Tất cả thao tác chính dùng được bằng bàn phím, có focus rõ và vùng chạm tối thiểu 44 px trên mobile.
- Loading, empty, error dùng câu chữ thân thiện, chỉ dẫn bước tiếp theo. Không che lỗi API quan trọng sau hiệu ứng.

## Cách triển khai

1. Tạo token màu, chữ, khoảng cách, radius, shadow và motion trong CSS; thay shell, nút, thẻ, badge, thông báo trước để toàn app có nền tảng chung.
2. Chỉnh từng luồng: đăng nhập và học sinh; nguồn/bài học và biên tập; duyệt/xuất bản/lịch sử; lớp/tiến độ và audit.
3. Kiểm tra bằng lint, typecheck, Vitest, build; xem màn 390/768/1280 px và chạy Playwright với stack đã seed nếu có. Kiểm tra focus, reduced motion, dark mode và không lộ lời giải trước khi nộp.

## Rủi ro và quyết định còn mở

- Dữ liệu seed có thể chưa đa dạng để kiểm tra mọi trạng thái; dùng mock UI có nhãn rõ khi cần kiểm tra giao diện. Không đổi backend để phục vụ riêng phần trình bày.
- Quyết định chi tiết về icon/họa tiết, câu chữ vi mô và tinh chỉnh khoảng cách thuộc phần triển khai, miễn giữ ý định và giới hạn trên.
