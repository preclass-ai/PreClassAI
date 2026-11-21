# Pháp lý dữ liệu cá nhân và AI trong nhà trường (cần rà soát trước khi nộp)

**Trạng thái kiểm chứng (21/11/2026).** Mỗi dòng ghi nguồn đã đọc được. Dòng nào ghi "cần đối chiếu văn bản gốc" thì chưa được xác nhận từ nguồn nào, đừng viện dẫn số điều.

## Căn cứ cần ghi trong Proposal, ADR và threat model
| Căn cứ | Đã kiểm chứng | Cần đối chiếu văn bản gốc |
|---|---|---|
| Nghị định 356/2025/NĐ-CP | Có hiệu lực từ 01/01/2026, hướng dẫn Luật Bảo vệ dữ liệu cá nhân 2025 và thay Nghị định 13/2023/NĐ-CP (luatvietnam.vn). Nêu thêm: hạn phản hồi yêu cầu của chủ thể dữ liệu (xóa: 20 ngày, hoặc 30 ngày với bên xử lý), bên kiểm soát phải lưu bằng chứng đồng ý và không đặt mặc định đồng ý, hồ sơ đánh giá tác động xử lý và chuyển dữ liệu xuyên biên giới. | Ngày ban hành; điều khoản về trẻ em và ngưỡng tuổi (trang không nêu trong phần đọc được). |
| Luật Bảo vệ dữ liệu cá nhân số 91/2025/QH15 | Chỉ có tên và số hiệu qua đường dẫn và qua Nghị định 356. Trang thuvienphapluat.vn trả lỗi 403 nên chưa đọc được nội dung. | Ngày thông qua, ngày hiệu lực, điều khoản về trẻ em và đồng ý của cha mẹ. |
| Công văn 5588/BGDĐT-GDPT | Là công văn ngày 19/08/2026 gửi các Sở GDĐT hướng dẫn triển khai giáo dục AI từ năm học 2026-2027 (moet.gov.vn, baovanhoa.vn). Khung nội dung được ban hành bằng Quyết định 2422/QĐ-BGDĐT ngày 18/08/2026, không phải bằng công văn 5588. Nêu: 12 tiết mỗi lớp mỗi năm cho nội dung cốt lõi; cơ sở rà soát công cụ AI theo độ tuổi và điều khoản sử dụng; không bắt học sinh dùng tài khoản cá nhân hoặc công cụ chưa rà soát; tuân thủ pháp luật về dữ liệu cá nhân; có quy trình tiếp nhận, xử lý, báo cáo sự cố liên quan AI. | Phạm vi theo từng khối lớp (trang không ghi rõ). |

Sửa so với bản trước của tài liệu này: công văn 5588 không phải văn bản "về giám sát việc dùng AI" mà là công văn hướng dẫn triển khai khung nội dung giáo dục AI.

## Đã đáp ứng trong sản phẩm (xem mã và tài liệu)
- Không lưu họ tên học sinh, chỉ mã khảo sát hoặc mã đăng nhập; câu hỏi HABIT AI được che số điện thoại, email, địa chỉ trước khi lưu hoặc gửi mô hình.
- Mô hình ngôn ngữ chỉ chạy khi học sinh bấm; nội dung đến học sinh đều do giáo viên duyệt; AI không tự duyệt.
- Giáo án thật chỉ đọc cục bộ, tên giáo viên bị loại ngay khi đọc (xem THREAT-MODEL-habit L-01).
- Giáo viên chỉ thấy câu hỏi đã ẩn danh của lớp mình, không xếp hạng học sinh.

## Việc còn thiếu (ghi trung thực)
- **Trang "Dữ liệu của em đi đâu"** đã có ở `/du-lieu` (link ở đăng nhập, `/thu` và khu vực học sinh). Thời hạn lưu ghi trên trang: 90 ngày sau khi đợt khảo sát kết thúc rồi xóa (quyết định của nhóm, ngày 21/11/2026). **Chưa có việc tự động xóa**: đến hạn phải chạy tay `scripts/ops/purge_guests.py`; cần người phụ trách nhớ ngày. Trang không nêu nơi xử lý của nhà cung cấp AI ngoài tên máy chủ trong cấu hình (nơi đặt máy chủ của họ chưa kiểm chứng).
- Quy trình báo cáo sự cố theo công văn 5588 chưa viết: cần người chịu trách nhiệm và kênh báo.
- Đánh giá tác động xử lý dữ liệu cá nhân (nếu luật mới yêu cầu) chưa làm.
