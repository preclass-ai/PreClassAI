# PR A: câu chữ và nhận diện (feat/team-copy)

Base: `main` (f627e82). Áp skill humanizer: câu ngắn, xưng "em", bỏ sáo rỗng, không gạch dài.

## Đổi gì
- Login: "hành trình học tập của em", nhãn "Gia sư AI cá nhân", "Cùng học", bỏ khẩu hiệu "Mỗi câu hỏi là một khám phá" và dòng "Địa lí 10–11 • Học để hiểu thế giới", bỏ nhãn tọa độ trang trí.
- Header "Học trước, hiểu sâu". Trang học sinh: "Hành trình học tập", "Hôm nay em học gì?", "Bài tập của em", "Cần làm tiếp", "Đã xong". Thẻ bài giữ nhãn môn: "Địa lí · 10A1".
- Tên lớp: cột `class.name` (migration 0006, thêm), lớp KS hiện "10A1"; `className` trong `GET /v1/student/assignments`. Mã `KS` và mã khảo sát `KS-XXXX` không đổi.
- Banner mã khảo sát viết lại ngắn. Mẫu từ chối của Habit không còn gạch dài.
- Không còn "—" hoặc " – " trong chuỗi UI (ô trống hiện "Chưa có"/"Không có"); test quét ở web và API.
- Seed: bỏ "(DỮ LIỆU MINH HỌA)" khỏi tiêu đề và đoạn văn học sinh đọc; thêm một dòng "Số liệu dùng để luyện tập." dưới bảng. `check_seed_leak.py` 0 vi phạm.

## Không làm: thay số liệu seed bằng số thật
Chỉ xác minh được 2 trên 4 vùng của bài dân cư (và nso.gov.vn không mở được từ máy dev), nên giữ số luyện tập. Chi tiết, nguồn đã xác minh và việc còn lại: `.agents/DATA-SOURCES.md`. **Cần một người mở được nso.gov.vn tra 2 con số còn thiếu** nếu muốn bài thật trước 25/11.

## Kiểm tra
ruff, mypy --strict sạch; pytest 337 passed (test_blocks cập nhật 18→19 khối); OpenAPI và `schema.d.ts` sinh lại; web lint, typecheck sạch, vitest 58 passed. Playwright xem báo cáo cuối PR.
