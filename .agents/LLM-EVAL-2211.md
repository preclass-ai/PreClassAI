# Đánh giá model cho HABIT AI (22/11/2026)

Chạy bằng `scripts/ops/llm_smoke.py` (17 câu qua model: 10 câu hỏi và 7 câu tấn công vượt qua bộ nhận diện ý định) với cùng bộ lọc như API. Dữ liệu là bài seed (số liệu luyện tập), không có dữ liệu học sinh. Không có khóa trong tài liệu này.

## Nguyên nhân lỗi cũ
`llm_smoke.py` báo `HTTPError` cho mọi câu vì `urllib` gửi User-Agent mặc định (`Python-urllib/3.x`), mà Groq (qua CDN) từ chối. Thêm `User-Agent: PreClassAI/1.0` là chạy được. Từ nay lỗi in rõ mã trạng thái và tối đa 300 ký tự nội dung, không in khóa hay header.

## Kết quả
| | qwen/qwen3.8-27b | openai/gpt-oss-120b |
|---|---|---|
| Lỗi HTTP | 0 | 0 |
| Vi phạm (lộ đáp án, nhận định phương án, PII, lộ prompt) | 0 | 0 |
| Token vào / ra trung bình mỗi lượt | 323 / 42 | 395 / 91 |
| Thời gian trung bình | 0,39 s | 0,71 s |
| Câu bị bộ lọc bỏ (rơi về luật) | 4 trên 17 | 2 trên 17 |
| Có phần suy nghĩ trong phản hồi | không | không |
| Tiếng Việt | tự nhiên, ngắn, bám bài; đôi khi gọi "bạn" (đã sửa trong prompt) | dài hơn; có lần nói "sách giáo khoa lớp 10, mục ..." không có trong bài |

## Chọn
Model chính `qwen/qwen3.8-27b`, dự phòng `openai/gpt-oss-120b` (cùng khóa và base URL). Lý do: ít token hơn một nửa ở phần trả lời, nhanh hơn, bám nội dung bài hơn. gpt-oss có lần nhắc tới nguồn không có trong bài (không phải vi phạm theo bộ lọc, nhưng là thông tin chưa được duyệt).

Tham số đã dùng (kiểm bằng request thật): `stream=false`, `max_completion_tokens=220`; qwen: `temperature=0.5, top_p=0.95, reasoning_effort=none, reasoning_format=hidden`; gpt-oss: `temperature=0.5, top_p=1, reasoning_effort=low, include_reasoning=false`. Groq nhận cả bốn tham số cho từng model, không trả 400.

## Red team thật
`habit_redteam.py --live --max-calls 150` với qwen: 150 lượt gọi thật, 0 vi phạm, 7 phản hồi bị bộ lọc bỏ (dùng câu luật thay thế). Chạy mô phỏng (không mạng): 0 vi phạm.

## Chi phí
Trung bình khoảng 365 token mỗi lượt (qwen). Ngân sách `CHAT_DAILY_TOKEN_BUDGET=150000` cho khoảng 410 lượt model mỗi ngày; mỗi học sinh tối đa 30 lượt hỏi mỗi ngày nên 14 học sinh dùng hết hạn mức cá nhân trước khi chạm ngân sách. Hết ngân sách thì API tự dùng luật.

## Khuyến nghị cho ngày thi
`CHAT_MODE=llm` được (0 vi phạm trên 150 lượt thật), nhưng luật là phương án chắc chắn: nếu Groq lỗi hoặc chậm thì API tự về luật, học sinh không thấy lỗi. Chưa kiểm: tải đồng thời nhiều học sinh cùng lúc (giới hạn 30 yêu cầu mỗi phút của gói miễn phí). Phần "gợi ý thêm" (`CHAT_AI_EXTRA`) vẫn để tắt.
