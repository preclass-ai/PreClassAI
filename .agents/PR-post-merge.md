# PR: khôi phục nội dung mất sau các merge trên GitHub web, sửa lỗi Personalization (fix/post-merge-main)

Base: `main` (e4f1604). Không force push.

## Đã mất/sai trong main (so với bản đã kiểm 3ad8d03 và 44d0746 cho Upload, 08e938d cho Personalization)
| Chỗ | Tình trạng trong main | Xử lý |
|---|---|---|
| `apps/api/app/config.py` | thiếu 6 biến `source_*` (b6c0909) → `get_settings().source_*` lỗi, CI mypy fail | khôi phục |
| `apps/web/app/globals.css` | thiếu khối upload (`.dropzone*`, `.anchor-preview*`); Habit/Personalization còn đủ | khôi phục |
| `docs/api/API_GUIDE.md` | thiếu mục Upload; Habit đứng mục 12, Personalization 13 | Upload 12, Habit 13, Personalization 14 |
| `docs/api/DATA_MODEL.md` | thiếu mục "Nguồn từ nhiều định dạng" | khôi phục |
| `docs/operations/RUNBOOK.md` | thiếu mục "Giới hạn nạp tệp" (mất từ merge #26, kể cả ở 3ad8d03 và nhánh upload sau khi merge main; lấy lại từ 44d0746) | khôi phục |
| `.agents/DECISIONS_AGENT.md` | thiếu mục "Upload nhiều định dạng" | khôi phục |
| `apps/api/tests/unit/test_contract.py` | 49, trong khi openapi có 50 operation (44 + 1 upload + 2 habit + 3 personalization) | 50, đếm thật từ `openapi.json` |
Đã kiểm và **đúng**: toàn bộ code Habit và Personalization (backend, web, test, migration 0003/0004, ADR) trùng 08e938d; toàn bộ code Upload (formats, parse, service, fixtures, source-form, anchors, test) có đủ. `openapi.json` và `schema.d.ts` sinh lại từ code: không đổi (đã khớp).

## Lỗi thật tìm thấy khi chạy Playwright Personalization (chưa từng chạy trước đó)
Checkbox lựa chọn "giật" về trạng thái cũ cho đến khi server trả lời; hai click liên tiếp có thể bị trả lời đến sai thứ tự ghi đè nhau. Sửa trong `personalization.tsx`: cập nhật đồng bộ bằng state cục bộ, chỉ phản hồi cuối cùng mới ghi đè, hoàn tác khi lỗi. Chế độ Tập trung ẩn luôn phần đầu bài (hero, đường dẫn) cho đúng "ẩn thành phần phụ". Spec Personalization đổi sang học sinh HS10-13/14/15/11 để không trùng habit.spec.

## Kiểm tra (local, đúng các bước CI)
- `ruff check .` sạch; `mypy --strict app` sạch; pytest 331 passed, 1 skipped; OpenAPI khớp code (test_contract) và `schema.d.ts` không đổi sau `gen:api`.
- Web: lint, typecheck sạch; vitest 57 passed; `next build` biên dịch + sinh trang thành công (trên Windows bước đóng gói standalone báo EPERM, đặc thù Windows).
- Red team Habit, mọi tổ hợp lựa chọn (chia nhỏ × ưu tiên bảng): 0 vi phạm.
- Playwright từng viewport, một lần một: flag tắt (auth, student, teacher): 390 ✓ (teacher lỗi 1 lần do dev server biên dịch lần đầu, chạy lại ✓), 768 ✓, 1280 ✓, WebKit: 4/5 (teacher "inspects a block" lỗi do ảnh fullPage vượt 32767 px của WebKit, không phải lỗi ứng dụng; chưa đổi test). Flag bật: habit 4/4, upload 4/4 (2 test mỗi viewport), personalization 4/4 sau khi sửa.
- Ảnh S07 chế độ Tập trung: `apps/web/test-results/personalization/focus-{mobile-390,tablet-768,desktop-1280,webkit-390}.png` (thư mục gitignored).

## Rủi ro
`RLIMIT_AS` của parser upload chưa thử trên Linux. Test teacher WebKit nên đặt `fullPage` có điều kiện (ngoài phạm vi PR này).
