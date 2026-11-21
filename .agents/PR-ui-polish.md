# UI polish pass và đổi tên HABIT AI (nằm trong feat/habit-ai-v2, xếp chồng trên feat/team-copy)

Merge `feat/team-copy` (PR A) trước. Không đổi logic hay API; chỉ giao diện và chữ.

## Đổi tên
Mọi chữ hiển thị "Habit" thành "HABIT AI": nút "Hỏi HABIT AI", "HABIT AI giải thích", tiêu đề chat, ô nhập, thông báo lỗi, mẫu trả lời và prompt hệ thống. Test: `tests/copy.test.ts` (không còn từ "Habit" riêng lẻ trong chuỗi UI), `tests/unit/test_copy.py` (mẫu trả lời và prompt).

## Trang học sinh
- Hero thấp hơn (~60%), chữ giới hạn 58% bề rộng, họa tiết dời sang phải, mờ (opacity 0,3); ẩn họa tiết ở 390.
- Mã khảo sát là một chip một dòng dưới hero ("Mã khảo sát: KS-XXXX" + biểu tượng sao chép, báo "Đã chép" 2 giây). Trang bài học cũng dùng chip này.
- Một dải thống kê: "1 bài cần làm · 0 bài đã xong" và chuỗi ngày HABIT AI ("🔥 n ngày, mục tiêu x/3", chỉ khi HABIT AI bật). Bỏ ô "bài được giao".
- Thẻ bài: "Địa lí · 10A1", hạn dd/mm/yyyy, thanh tiến độ có nhãn "0/2 câu", nút "Làm bài / Làm tiếp / Xem lại".
- Bố cục: trang danh sách rộng tới 1120px (trước đó bị bó 680px), trang bài học 820px.

## Thẻ câu hỏi
- Chip "Câu 1" đặc, chip kỹ năng màu theo kỹ năng (So sánh, Tính toán, Đọc bảng).
- "Gợi ý 1/3" (biểu tượng bóng đèn) và "Hỏi HABIT AI" (biểu tượng HABIT AI) là nút ghost một hàng nhỏ dưới đề, vẫn cao 44px.
- Phương án: cao 56px, viền mảnh, chữ ~17px, chọn có viền, nền, chữ đậm; radio đã sửa lỗi bị bọc hộp xám; có focus rõ.
- Nút Nộp: chưa chọn thì xám rõ (chữ muted trên nền surface-2, đạt AA) kèm dòng "Chọn một đáp án để nộp."; chọn rồi thì nút chính. Tên nút giữ "Nộp câu trả lời" để E2E và trình đọc màn hình không đổi.
- Chat: tiêu đề có nền gradient, chấm "đang trực tuyến", "HABIT AI đang nghĩ" với 3 chấm (tắt khi reduced-motion).

## Kiểm tra
ruff, mypy --strict sạch; pytest 339 passed. Web lint, typecheck sạch, vitest 59. Playwright từng viewport, hai pha (reset DB giữa pha): auth + teacher + student (390, 768, 1280, WebKit) 5/5 mỗi viewport; habit + personalization + upload 4/4 mỗi viewport. Ảnh: `.agents/screens-polish/before` và `.../after` (390 và 1280: trang học sinh, thẻ chưa chọn/đã chọn/đã nộp, chat, trang khách có chip mã).

## Còn lại (thuộc PR B, chưa làm trong đợt này)
Chip "Em nên bắt đầu từ đâu?" vẫn bị trả "nằm ngoài bài học" (thấy trong ảnh chat), sửa ở PR B mục 8.
