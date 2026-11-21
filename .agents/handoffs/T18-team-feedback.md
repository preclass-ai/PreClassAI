# Handoff: T18 — góp ý của team (câu chữ, HABIT AI v2, góc nhìn giáo viên)

Status: `in_progress` · Owner/harness: Claude Code · Date: 2026-11-22

## Skills đã dùng
| Skill | Bước | Kết quả |
|---|---|---|
| humanizer | PR A: mọi chuỗi UI; mẫu trả lời Habit | Bỏ dấu gạch dài, khẩu hiệu sáo, tin lặp (chân trang đăng nhập); test quét `copy.test.ts` và `test_copy.py`. |
| web-design-guidelines | PR A: ảnh 390/1280 | Không phát hiện lỗi mới (chỉ đổi chữ). |
| playwright-cli | PR A | auth, student 4 viewport xanh; ảnh trong `.agents/screens-copy/` (không commit). |
| design-taste-frontend (variance 4, motion 3, density 5) | PR B: polish + chat | Token sẵn có, không thêm thư viện; hero thấp, chip mã khảo sát, nút ghost, chat gradient. CSS ≤ 200 ms, tắt khi reduced-motion. |
| web-design-guidelines | PR B | Tự kiểm: tương phản AA (nút Nộp xám, chip), mục tiêu bấm ≥ 44px, focus rõ, `role=status`, label cho mọi nút biểu tượng. Chưa chạy bản audit tải luật như đợt trước. |
| security-threat-model | PR B: phần "gợi ý thêm", nút gợi ý | `THREAT-MODEL-habit.md` thêm H-17..H-20 (mỗi mối đe dọa có biện pháp và test). |
| security-best-practices | PR B | Review code: `quick` là enum cố định, bỏ qua `message`; `postcheck_extra` không tin đầu ra model; khóa chỉ ở env. |
| playwright-cli | PR B | habit.spec 4 viewport; bắt lỗi bảng chat cao hơn màn hình ở 1280. |
| security-threat-model | PR C: góc nhìn giáo viên | `THREAT-MODEL-habit.md` thêm H-21 (ẩn danh, quyền lớp) và H-22 (gửi dữ liệu cho AI phân tích). |
| security-best-practices | PR C | Quyền theo lớp (404 không 403), phản hồi chỉ có số đếm và văn bản đã che PII, prompt bọc `<data>` và vô hiệu ngoặc nhọn. |
| humanizer | PR C | Câu chữ giáo viên: ngắn, không gạch dài (test quét chuỗi UI vẫn chạy). |
| playwright-cli | PR C | insights.spec 4 viewport; ảnh `.agents/screens-insights/`. |
