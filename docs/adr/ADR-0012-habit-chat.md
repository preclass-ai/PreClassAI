# ADR-0012: Habit, trợ lý học từng bước cho học sinh

Trạng thái: đề xuất (chờ Khải duyệt) · Ngày: 2026-11-20 · Liên quan: `docs/security/THREAT-MODEL-habit.md`, `docs/ui/HABIT-DESIGN.md`, ADR-0010, PR-08.

## Bối cảnh

Học sinh làm bài trước, xem lời giải sau (PR-08). Học sinh khối 10–11 cần trợ giúp **trong lúc làm** mà không phá luận điểm "mọi nội dung đến học sinh đều đã được giáo viên duyệt". Ràng buộc: chi phí mặc định 0đ, Render Free 512 MB, không thêm dịch vụ trả phí hay thư viện lớn.

## Quyết định

1. **Mặc định tắt và không tốn tiền.** `CHAT_ENABLED=false`; khi bật, `CHAT_MODE=rule` (mẫu câu theo kỹ năng, không gọi LLM). Chế độ `llm` là tùy chọn, chỉ chạy khi học sinh bấm, mặc định không có khóa.
2. **Chỉ dùng nội dung đã duyệt.** Habit đọc `published_version.snapshot` của bài học sinh được giao (cùng cổng `student._load`: thành viên lớp, đã mở, chưa thu hồi; sai → 404). Không đọc nguồn, provenance, review, bài khác. Không thêm trường vào snapshot (snapshot bất biến và có hash); "Habit view" được dựng lúc gọi từ chính snapshot.
3. **Không bao giờ lộ đáp án trước khi nộp**: nhãn đúng, giá trị, xác nhận/phủ định từng phương án, loại trừ dần. Ba lớp: (a) nhận diện ý định bằng luật **trước** mọi thứ, kể cả LLM (có dấu và không dấu); (b) gợi ý là mẫu tĩnh không phụ thuộc đáp án nên hỏi nhiều lần cũng không ghép ra thông tin; (c) `rules.leak` kiểm mọi phản hồi (rule và LLM) trước khi gửi, thêm kiểm số (VAL-03: số phải thuộc nội dung đã duyệt). LLM không bao giờ nhận `answer_key`/`explanation` của câu chưa nộp.
4. **Giải thích** (`explain`) chỉ sau khi chính học sinh đã nộp câu đó, nguyên văn `explanation` đã duyệt, không qua LLM.
5. **Dữ liệu**: ba bảng mới chỉ thêm (`chat_session`, `chat_message` append-only bằng trigger, `study_activity`). PII (SĐT, email, địa chỉ) bị che trước khi lưu và trước khi gửi LLM. CSV khảo sát chỉ có số đếm, không có văn bản chat.
6. **Chi phí và an toàn vận hành**: 30 lượt/ngày/học sinh, 6 lượt/câu, tin nhắn ≤ 300 ký tự, `CHAT_MAX_OUTPUT_TOKENS=220`, ngân sách ngày `CHAT_DAILY_TOKEN_BUDGET=300000` (hết thì rơi về rule), timeout 15 s và tối đa 2 cuộc gọi LLM đồng thời, cache trong ngày theo (câu, bậc, câu hỏi chuẩn hóa).
7. **Thói quen** (streak theo ngày Asia/Ho_Chi_Minh, mục tiêu 3 câu/ngày, huy hiệu Tự lực/Kiên trì/Thám hiểm) tính từ dữ liệu có sẵn, không có điểm xếp hạng giữa học sinh.

## Lựa chọn đã cân nhắc

- **LLM làm mặc định**: bị loại (chi phí, rủi ro rò đáp án mang tính xác suất, gửi nội dung ra bên thứ ba). Giữ làm tùy chọn có hậu kiểm.
- **Thêm trường "habit view" vào snapshot lúc publish** (đề bài gợi ý): bị loại vì làm đổi hash/immutability của snapshot và cần migrate bài cũ; dựng từ snapshot khi gọi đủ dùng.
- **Hỏi tự do khắp bài**: bị loại; mỗi lượt gắn với một câu để giới hạn phạm vi và lộ trình hạn mức.

## Hậu quả và rủi ro còn lại

- Seed hiện hiển thị khối `data_fact` chứa giá trị lớn nhất, đồng thời là đáp án câu MCQ đầu: học sinh thấy sẵn ở S07, Habit không làm tệ thêm nhưng không che. Là lỗi nội dung của giáo viên, cần dặn.
- Hậu kiểm chế độ `llm` bắt được các mẫu đã biết, không chứng minh được "không bao giờ": cần chạy `scripts/ops/habit_redteam.py` và red team với model thật trước khi bật; cần đồng ý của trường trước khi gửi nội dung bài ra LLM bên ngoài.
- Danh sách từ khóa không bao phủ hết tiếng lóng; hậu quả bị chặn bởi việc luật không chứa đáp án.
- Cache phản hồi LLM nằm trong RAM một tiến trình (≤ 200 mục), mất khi restart.
