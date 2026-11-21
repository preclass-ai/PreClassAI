# Pháp lý dữ liệu cá nhân và AI trong nhà trường (cần rà soát trước khi nộp)

**Cảnh báo:** các căn cứ pháp lý dưới đây do nhóm cung cấp (ngày 21/11/2026), tôi chưa tra cứu được văn bản gốc từ máy này. Hãy đối chiếu số hiệu, ngày hiệu lực và điều khoản với bản chính thức (Cổng thông tin Chính phủ, Công báo) trước khi đưa vào hồ sơ.

## Căn cứ cần ghi trong Proposal, ADR và threat model
- Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 (hiệu lực 01/01/2026) và Nghị định 356/2025 hướng dẫn, thay Nghị định 13/2023 (theo thông tin nhóm cung cấp). ADR-0013 hiện viện dẫn Nghị định 13/2023: cần cập nhật khi xác nhận văn bản mới.
- Công văn 5588/BGDĐT-GDPT (2026) về giám sát việc dùng AI, bảo vệ dữ liệu và báo cáo sự cố (theo thông tin nhóm cung cấp, chưa đọc nội dung).

## Đã đáp ứng trong sản phẩm (xem mã và tài liệu)
- Không lưu họ tên học sinh, chỉ mã khảo sát hoặc mã đăng nhập; câu hỏi HABIT AI được che số điện thoại, email, địa chỉ trước khi lưu hoặc gửi mô hình.
- Mô hình ngôn ngữ chỉ chạy khi học sinh bấm; nội dung đến học sinh đều do giáo viên duyệt; AI không tự duyệt.
- Giáo án thật chỉ đọc cục bộ, tên giáo viên bị loại ngay khi đọc (xem THREAT-MODEL-habit L-01).
- Giáo viên chỉ thấy câu hỏi đã ẩn danh của lớp mình, không xếp hạng học sinh.

## Việc còn thiếu (ghi trung thực)
- **Trang "Dữ liệu của em đi đâu"** chưa có trong giao diện. Nội dung cần nêu: nhà cung cấp mô hình và nơi xử lý (Groq tại Mỹ, DeepSeek tại Trung Quốc: chỉ gửi câu hỏi đã che thông tin cá nhân và đoạn nguồn đã duyệt), thời hạn lưu (nhóm cần quyết định, hiện lưu đến khi xóa dữ liệu khảo sát), cách xóa (liên hệ giáo viên hoặc quản trị; script `purge_guests.py` xóa dữ liệu khách).
- Quy trình báo cáo sự cố theo công văn 5588 chưa viết: cần người chịu trách nhiệm và kênh báo.
- Đánh giá tác động xử lý dữ liệu cá nhân (nếu luật mới yêu cầu) chưa làm.
