# Sửa 4 bug reviewer báo (22/11/2026), handoff

Nhánh `fix/reviewer-bugs`. Toàn bộ thay đổi nằm ở backend, **cần Khải review**. Phía FE chỉ có `schema.d.ts` được sinh lại (mô tả `rule` đổi từ VAL-10 thành VAL-11).

## Bug và cách sửa
1. **Câu hỏi thiếu số liệu nhưng vẫn pass** (4 vùng, đề hiện 2, đáp án và giải thích dùng 4). Thêm luật **VAL-11** (BLOCKER) trong `app/validation/__init__.py`. Các số nguồn mà đáp án dựa vào phải hiện ra trước khi học sinh trả lời, gồm toán hạng của `derivation` và các số trong lời giải có trong nguồn của bài. Kết quả tính ra (tổng, hiệu) không có trong nguồn nên không bị bắt. Ràng buộc DB đã cho phép VAL-01..19 (migration 0005), nên không cần migration mới.
   - Hạn chế đã biết: lời giải trích thêm số nguồn không cần cho câu hỏi cũng bị chặn. Giáo viên sửa lời giải hoặc thêm dòng số liệu.
2. **Hạn nộp lệch** (giáo viên thấy 20/12/2026, học sinh thấy 20/11/2027). Đây là lỗi seed, không phải lỗi format ngày: lớp 10A1 có hạn +30 ngày, lớp khảo sát KS (cũng tên "10A1") có hạn +365 ngày. `seed/survey.py` giờ đặt hạn của bài seed ở 10A1 bằng hạn ở KS. DB demo cần chạy lại `python -m seed.survey` thì mới có hiệu lực.
3. **"Có ít nhất một câu hỏi" được tick khi bài không có câu hỏi.** Cổng `HAS_ITEMS` từng tính cả `card_front`. Giờ cổng chỉ tính `worksheet_item`. Bài chỉ có thẻ ghi nhớ không xuất bản được nữa, vì học sinh không trả lời được thẻ nên bài cũng không bao giờ "Đã xong".
4. **HABIT AI trả lời "đọc kỹ lại" khi học sinh hỏi số liệu ở đâu.** `build_view` từng bỏ hẳn `data_fact`. Hệ quả là gợi ý bậc 2 chỉ về "tiêu đề và đoạn văn", còn ở chế độ LLM câu trả lời nhắc tới số liệu bị `number_ok` loại rồi rơi về câu mẫu. Giờ:
   - `ItemView.facts` chứa các dòng số liệu học sinh đang thấy, và số của chúng được tính là số hợp lệ.
   - Gợi ý bậc 2 chỉ rõ các dòng số liệu in đậm phía trên câu hỏi. Số dòng viết bằng chữ, vì chữ số có thể trùng đáp án.
   - Prompt LLM nhận khối "Số liệu học sinh đang thấy" và được dặn chỉ thẳng dòng cần dùng. Lớp chặn lộ đáp án giữ nguyên.

## Kiểm tra
`uv run ruff check .`, `uv run mypy --strict app`, `uv run pytest`: 461 pass, 1 skip, chạy với Postgres. Test mới: `tests/unit/test_val11_data_shown.py`, `tests/unit/test_publish_gate.py`, 2 test trong `test_habit_rules.py`, 1 test trong `test_e2e_isolation.py`.

## Chưa làm
- Xưng hô "em" và "bạn" (góp ý của reviewer) chưa đổi. Prompt hiện ép gọi học sinh là "em". Đây là quyết định sản phẩm.
- Chưa chạy LLM thật (`scripts/ops/llm_smoke.py`) sau khi đổi prompt. Cần chạy trước khi bật `llm` trên staging.
