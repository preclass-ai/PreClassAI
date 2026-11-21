# Nguồn số liệu của bài seed

Trạng thái 22/11/2026: **chưa có bài nào dùng số liệu thật.** Số liệu trong 6 bài seed vẫn là số luyện tập do nhóm soạn, không phải số thống kê chính thức. Học sinh chỉ thấy một dòng nhỏ dưới bảng: "Số liệu dùng để luyện tập." Giáo viên thấy ghi chú giấy phép của nguồn nói rõ đây là số giả.

## Vì sao chưa thay
Bài "Phân bố dân cư theo vùng" cần số dân của 4 vùng cùng một năm từ cùng một bảng. Khi tra từ máy dev chỉ xác minh được một phần, và trang `nso.gov.vn` không mở được từ máy này (lỗi DNS khi tải thông cáo báo chí). Trộn số thật của hai vùng với số giả của hai vùng khác thì còn tệ hơn giữ nguyên, nên không thay.

## Đã xác minh được (Tổng điều tra dân số và nhà ở 0 giờ 1/4/2019)
| Điều | Giá trị | Nguồn |
|---|---|---|
| Tổng dân số cả nước | trên 96,2 triệu người | https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2019/12/thong-cao-bao-chi-ket-qua-tong-dieu-tra-dan-so-va-nha-o-nam-2019/ |
| Đồng bằng sông Hồng | 22,5 triệu người (gần 23,4% dân số), vùng đông dân nhất | cùng trang trên; https://baodautu.vn/dan-so-viet-nam-vuot-96-trieu-nguoi-d103737.html |
| Tây Nguyên | 5,8 triệu người, vùng ít dân nhất | https://baodautu.vn/dan-so-viet-nam-vuot-96-trieu-nguoi-d103737.html (báo dẫn kết quả tổng điều tra; cần đối chiếu với bảng của Tổng cục Thống kê) |

## Còn thiếu để thay bài (cần người truy cập được nso.gov.vn)
Số dân 2019 của Trung du và miền núi phía Bắc, Đông Nam Bộ (và Bắc Trung Bộ và Duyên hải miền Trung, Đồng bằng sông Cửu Long nếu muốn đủ 6 vùng), lấy từ bảng "Kết quả toàn bộ Tổng điều tra dân số và nhà ở 2019" hoặc Niên giám thống kê 2019 trên https://www.nso.gov.vn. Có đủ thì sửa `apps/api/seed/lessons.py` (bài `dan-so-vung`: 4 hàng, năm 2019, một đơn vị), thêm dòng "Nguồn: Tổng cục Thống kê, 2019." thay dòng luyện tập, chạy `check_seed_leak.py`, rồi cập nhật bảng trên.

Các bài khác (rừng, lúa, GDP, điện, xuất khẩu): chưa tra.
