# Góp ý UX của reviewer (22/11/2026), handoff

Nhánh `feat/web-reviewer-ux`. Phần lớn là frontend. Có hai thay đổi API nhỏ, **cần Khải review**: `AssignmentOut.lessonId` và `revisionNo`; `ClassOut.isSurvey`. OpenAPI và `schema.d.ts` đã được sinh lại.

## Đã làm
- **Màu trạng thái:** không đổi token theme nào. "Máy đã kiểm" vẫn tông `info` nhưng vẽ dạng viền rỗng (class `.badge-outline`, chỉ dùng trong `ReviewBadge`). "Đã duyệt" giữ dạng nền đặc `success` có dấu ✓, "Chưa kiểm" giữ màu xám.
- **Gợi ý theo mức độ** thay cho 1/2/3: nhẹ (Bắt đầu từ đâu), vừa (Dữ liệu cần dùng ở đâu), chi tiết (Cách làm). Tên các mức nằm ở `HINT_LEVEL` trong `src/lib/labels.ts`, dùng chung cho thẻ gợi ý của học sinh và cột "Gợi ý cao nhất" của giáo viên.
- **Nhãn trích dẫn trong gợi ý:** "Tài liệu giáo viên đã duyệt" đổi thành "Trích từ bài học".
- **Dữ liệu của em đi đâu** thành dropdown, **chỉ hiện cho khách**. Trang `/du-lieu` mô tả khảo sát ẩn danh, nên không đúng với học sinh có tài khoản.
- **Câu thông báo khách** được viết lại, giữ ý "không gắn với danh tính".
- **Làm xong bài:** thêm thông báo giải thích vì sao mỗi câu chỉ nộp một lần.
- **Trang lớp:**
  - Nút "Chọn bài để giao".
  - Mỗi bài giao ghi "Giao từ Bản #n", tên bài là link về bài gốc, kèm link "Mở phần giao bài". Tab này luôn giao bản mới nhất.
  - Lớp khảo sát được ghi "(khảo sát)" ở tab lớp và trong ô chọn lớp khi giao bài.
- **Xưng hô:** giáo viên là "thầy cô", học sinh là "em". Thông báo lỗi dùng chung cho cả hai vai trò thì không dùng đại từ. Phía web không còn chỗ nào xưng "bạn".

- **Bớt chữ thừa:**
  - Thông báo "Môi trường thử nghiệm" nằm một lần ở layout giáo viên, không lặp ở từng trang.
  - Khối có lý do không cần nguồn chỉ hiện lý do ở tooltip, inspector và màn duyệt. Câu cảnh báo chỉ còn khi chưa ghi lý do.
  - Phụ đề các trang giáo viên nói việc cần làm, không mô tả cơ chế bên trong.
  - Nhãn nguồn thống nhất: "Ai dùng được" (`VISIBILITY` trong `labels.ts`), "Bản #n", "Số đoạn".
- **Dữ liệu seed:**
  - Bỏ "(minh họa)" khỏi tên tài khoản.
  - Bỏ mã slug khỏi tên nguồn.
  - Bỏ lý giải "Dữ liệu minh họa" ở mọi liên kết nguồn; trước đây inspector hiện "Lý giải: Dữ liệu minh họa".
  - Dấu "DỮ LIỆU MINH HỌA" giữ ở `licenseNote` của nguồn. Seed chỉ áp dụng cho DB mới.

## Kiểm tra
- Web: lint, typecheck, vitest 70/70.
- API: ruff, mypy, pytest 455 pass, 1 skip.
- Đã xem trên trình duyệt ở local (học sinh, khách, giáo viên).
- Các test E2E dùng câu chữ cũ đã được cập nhật nhưng **chưa chạy**.

## Chưa làm
- Thông báo lỗi do backend trả về (`detail`) vẫn có chỗ xưng "bạn". Frontend hiển thị theo `code` nên học sinh và giáo viên hầu như không thấy các câu đó.
- Trang hướng dẫn (tutorial) cho người mới chưa làm.
