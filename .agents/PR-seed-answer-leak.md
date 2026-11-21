# PR: seed không lộ đáp án, VAL-10, sửa test WebKit, quy trình merge (fix/seed-answer-leak)

Base: `main` (2680454). Không đổi code ứng dụng ngoài VAL-10 và MockProvider.

## 1. Lỗi trong seed (đã sửa) và cách kiểm
Học sinh đọc được đáp án từ chính bài: (a) `data_fact` chỉ có đúng hàng lớn nhất = đáp án câu 1; (b) đoạn văn thứ hai của 5/6 bài nêu hoặc gợi ý đáp án ("nhóm ngành dịch vụ chiếm tỉ trọng lớn nhất"); (c) đề câu 2 nêu tên đúng hai vùng (đáp án câu 1 nằm trong đó); (d) đáp án MCQ **luôn là A** ở cả 6 bài.
Sửa: mỗi hàng bảng là một `data_fact` (khối `df`, `df1..3`); đoạn thứ hai trung tính; đề câu 2 không nêu tên; thứ tự hàng đổi để đáp án đúng ở A/B/C/D khác nhau (C,B,D,A,C,B). MockProvider sinh đủ `data_fact` các hàng và đề trung tính (nếu không mọi bài sinh ra đều bị VAL-10 chặn).
- **VAL-10** (`app/validation/leak.py`, chạy trên `worksheet_item`, mọi môn): Chặn: số đáp án xuất hiện ở khối khác; đoạn nêu phương án đúng kèm "nhất/đứng đầu"; số liệu chỉ nêu đúng phương án đúng. Cảnh báo: từ chỉ có ở phương án đúng trong câu xếp hạng; đoạn/câu khác chỉ nêu một phần phương án gồm đáp án. Migration 0005 chỉ nới CHECK `ck_validation_rule` (01..09 → 01..19).
- `scripts/ops/check_seed_leak.py`: 12 câu / 6 bài, **0 vi phạm**, đáp án ở 4 vị trí (A1 B2 C2 D1). `tests/unit/test_seed_leak.py` chạy cùng kiểm tra, kèm test chứng minh các kiểu lộ cũ bị bắt (và "bảng" không bị nhầm với "bằng").
- Red team Habit lại (59 tấn công × 12 câu × 4 tổ hợp lựa chọn, rule + llm-mock): **0 vi phạm**.

## 2. Test WebKit "inspects a block"
Lỗi do ảnh `fullPage` của trang duyệt dài hơn 32767 px (giới hạn WebKit). Chỉ đổi test: `fullPage` tắt cho `webkit-390` (3 ảnh trong teacher.spec). Không đổi code app.

## 3. RUNBOOK
Mục "Quy trình merge" (CI xanh + báo cáo test; không resolve conflict trên GitHub web; từng nhánh một, gộp main vào nhánh kế tiếp trước khi merge) và mục "Seed và dữ liệu khảo sát".

## Kiểm tra (local, theo CI)
ruff, mypy --strict sạch; pytest 336 passed, 1 skipped; OpenAPI + `schema.d.ts` sinh lại từ code; web lint, typecheck sạch, vitest 57 passed. Playwright từng viewport (390 → 768 → 1280 → WebKit): auth + teacher 4/4 mỗi viewport (WebKit đã xanh), student (390 lỗi 1 lần do dev server biên dịch lần đầu, chạy lại xanh), habit và personalization 4/4 với seed mới.

## Cần quyết trước khi merge
**DB demo trên Render đã seed nên KHÔNG đổi** (seed bỏ qua khi đã có dữ liệu): bài khảo sát vẫn lộ đáp án và đáp án vẫn luôn là A cho đến khi reset + seed lại, mà reset xóa bài làm của học sinh. Nếu đợt khảo sát đã chạy: xuất `survey.csv` trước và coi dữ liệu câu hỏi cũ là không đáng tin; nếu chưa chạy: reset ngay sau merge.
