# ADR-0014: Đọc giáo án CV 5512 làm nguồn của bài chuẩn bị trước giờ học

Trạng thái: chấp nhận (2026-11-21). Phạm vi: PR D1 (đọc và lưu cấu trúc); giao diện kiểm tra và tạo bài là PR D2.

**Quyết định.** Một bộ đọc theo luật (pdfplumber cho PDF có chữ, python-docx cho DOCX) tách tệp thành các bài, rồi dựng cây 5512: mục tiêu (mã năng lực), thiết bị, 4 hoạt động (mở đầu, hình thành kiến thức, luyện tập, vận dụng), khung kiến thức, bảng, chú thích hình, câu hỏi trắc nghiệm. Mô hình ngôn ngữ mặc định tắt và chỉ gán nhãn tiêu đề khi luật thất bại.

**Vì sao không để mô hình đọc.** Đáp án MCQ phải chắc chắn. Giáo án đánh dấu đáp án bằng gạch chân, đọc được từ hình học của trang (đường hoặc hình chữ nhật mỏng ngay dưới chữ cái). Đúng một gạch thì tin; còn lại hỏi giáo viên.

**Không phụ thuộc môn.** Chỉ hai bảng cấu hình theo môn (`SUBJECTS`, `COMPETENCY_CUES`) và `subject_competency`; môn chưa có danh mục thì mã năng lực để trống thay vì đoán.

**Chi phí.** pdfminer đọc khoảng 0,5 giây mỗi trang: tệp 42 trang mất 20 đến 35 giây, nên khi nạp qua API cần `Limits(timeout_s=120)` cho loại "plan" (mặc định 30 giây của nguồn thường là không đủ).

**Rủi ro còn lại.** Khoảng một nửa câu trắc nghiệm trong giáo án mẫu không có gạch chân nên cần giáo viên xác nhận; Ngày dạy thường không có trong tiêu đề; tên viết tự do giữa đoạn không bị che; OCR không hỗ trợ.
