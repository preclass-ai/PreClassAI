# ADR-0013: Cá nhân hóa dựa trên hành vi và lựa chọn của học sinh

Trạng thái: đề xuất (chờ Khải duyệt) · Ngày: 2026-11-21 · Liên quan: ADR-0012 (Habit), `docs/security/data-inventory.md`.

## Quyết định

Cá nhân hóa chỉ dựa trên **hai nguồn**: (1) lựa chọn học tập do **chính học sinh** đặt và đổi bất cứ lúc nào, mặc định tắt; (2) **hành vi học** đã có sẵn trong hệ thống (kết quả lần làm đầu theo kỹ năng, số lần dùng gợi ý). Hệ thống **không thu, không suy luận và không lưu** bất kỳ nhãn tâm lý hay sức khỏe nào: không MBTI, không ADHD hay rối loạn nào, không trắc nghiệm tính cách, không "phát hiện" đặc điểm cá nhân, không phong cách học (visual/auditory...). Không có trường nào như vậy trong DB, API hay CSV; một test quét mã nguồn chặn các từ khóa này.

## Lý do

1. **Dữ liệu nhạy cảm của người chưa thành niên.** Thông tin về sức khỏe, đặc điểm tâm lý của học sinh là dữ liệu cá nhân nhạy cảm theo pháp luật về bảo vệ dữ liệu cá nhân, cần sự đồng ý riêng (với học sinh chưa thành niên, của cha mẹ hoặc người giám hộ), đánh giá tác động và biện pháp bảo vệ mà dự án này chưa có. Văn bản hiện hành: Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 (hiệu lực 01/01/2026) và Nghị định 356/2025/NĐ-CP, có hiệu lực từ 01/01/2026 và thay Nghị định 13/2023/NĐ-CP (trang luatvietnam.vn nêu rõ việc thay thế). Ngưỡng tuổi và điều khoản riêng về trẻ em của văn bản mới chưa đọc được từ nguồn nào: cần đối chiếu văn bản gốc trước khi viện dẫn số điều. (Cập nhật 21/11/2026, thay cho việc viện dẫn Nghị định 13/2023.) Không thu thì không phải gánh rủi ro rò rỉ, gắn nhãn sai hay phân biệt đối xử.
2. **Độ tin cậy khoa học.** Suy luận từ vài chục lượt bấm để kết luận tính cách hay rối loạn là không có cơ sở: MBTI có độ tin cậy kiểm-lại thấp, "phong cách học" không cho thấy cải thiện kết quả khi dạy theo phong cách, và không công cụ lớp học nào chẩn đoán ADHD được. Nhãn sai có hại hơn không có nhãn.
3. **Thiết kế phổ quát cho việc học (UDL).** Thay vì đoán "em này thuộc loại nào", cho **mọi** học sinh các lựa chọn trình bày giống nhau (chia nhỏ từng bước, hẹn giờ tập trung, ưu tiên bảng số liệu, ưu tiên giải thích, nhắc tiến độ). Em tự chọn theo nhu cầu hôm nay, không gắn nhãn cho em.

## Thiết kế

- Bảng `student_preference(student_id, key, value, updated_at)`; khóa cố định: `chia_nho_tung_buoc`, `hen_gio_tap_trung` (`off|5|10`), `uu_tien_bang_so_lieu`, `uu_tien_giai_thich`, `nhac_tien_do`, và `focus_mode_used` (dấu "đã dùng chế độ tập trung" cho khảo sát). Mặc định tắt (không có hàng). Học sinh xem/đổi/xóa hết của chính mình qua `GET|PUT|DELETE /v1/student/preferences`.
- Chế độ Tập trung (1 câu mỗi màn hình, thanh tiến độ, hẹn giờ và nhắc nghỉ ngắn) có cho mọi học sinh.
- Thích ứng theo hành vi bằng **luật** (0đ): kỹ năng có tỉ lệ sai lần đầu cao → gợi ý xem lại nội dung bài và hiện sẵn Gợi ý 1; kỹ năng làm tốt → giảm nhắc. Chỉ dùng điểm lần làm đầu và số lần xin gợi ý, không đoán đặc điểm cá nhân, không lưu kết luận (tính lại mỗi lần gọi).
- Habit đọc lựa chọn để đổi **cách trình bày** gợi ý (ngắn hơn, ưu tiên bảng). Mọi quy tắc không lộ đáp án vẫn áp dụng (red team chạy lại với mọi tổ hợp lựa chọn).
- Cờ `PERSONALIZATION_ENABLED` (mặc định tắt); tắt thì mọi route trả 404 và UI ẩn.
- Khảo sát: CSV thêm các lựa chọn dưới dạng cờ và `focus_mode_used`; không có trường tâm lý.

## Lựa chọn đã cân nhắc
- **Bài trắc nghiệm "phong cách học"/tính cách để gợi ý nội dung**: bị loại (lý do 1 và 2).
- **Suy luận "dễ mất tập trung" từ thời gian làm bài**: bị loại (gắn nhãn sức khỏe từ hành vi, không đáng tin).
- **LLM để cá nhân hóa**: bị loại (chi phí, dữ liệu học sinh ra ngoài); luật đủ cho phạm vi này.

## Hậu quả và rủi ro còn lại
Lựa chọn của học sinh là dữ liệu cá nhân (ít nhạy cảm) gắn với tài khoản: nằm trong phạm vi chính sách dữ liệu hiện có, xóa được bằng `DELETE`. Thích ứng theo hành vi có thể khiến một học sinh thấy nhiều lời nhắc hơn bạn bè; chỉ hiển thị cho chính em, không hiển thị cho giáo viên. Nếu sau này muốn báo cáo cho giáo viên theo kỹ năng, cần ADR riêng.
