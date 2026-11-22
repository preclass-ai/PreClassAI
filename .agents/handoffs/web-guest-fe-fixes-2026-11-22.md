# Sửa lỗi FE luồng khách (22/11/2026), handoff

Nhánh `feat/web-guest-fe-fixes`. Chỉ có frontend (`apps/web`), không đổi API hay OpenAPI. Bốn lỗi này được tìm ra khi test production (pre-class-ai.vercel.app) bằng tài khoản khách.

## Đã làm
- **Enter ở ô mã khảo sát** (`app/login/page.tsx`):
  - Lỗi cũ: cả trang đăng nhập là một `<form>`. Nhấn Enter ở ô mã thì gửi form tài khoản đang thu gọn, trình duyệt chặn vì có ô `required` bị ẩn, và không có gì xảy ra trên màn hình.
  - Giờ form tài khoản và form mã khảo sát là hai form riêng; khung ngoài là `<div>`. Form tài khoản vẫn giữ `method="post"`.
- **Sai mã khảo sát:**
  - `NOT_FOUND` hoặc `VALIDATION_ERROR` khi gọi `/guest/resume` thì hiện "Mã khảo sát không đúng…" ngay dưới ô nhập, kèm `aria-invalid` và `aria-describedby`.
  - Lỗi khác (ví dụ `RATE_LIMITED`) vẫn dùng `ErrorBox` chung.
  - Sửa lại mã thì lỗi tự xoá.
- **Khung "Cảm ơn em đã làm bài!"** (`GuestSurveyCard`) chỉ hiện khi đã làm hết các câu. Trước đây khung này hiện ngay khi mở bài. Mã khảo sát vẫn hiện ở banner đầu trang.
- **Ô đáp số:**
  - Thêm `parseAnswerNumber` trong `src/lib/format.ts`, thay cho `Number(value.replace(",", "."))`.
  - Đọc được `17,3`, `17.3`, `-2,5`, `1 234`, `1.234,5`, `1.234.567`. Một mình `1.234` vẫn hiểu là 1,234 như trước.
  - Từ chối `0x11`, `1e3`, `Infinity`; trước đây `Number()` âm thầm chuyển đổi các giá trị này.
  - Nhập chữ hoặc đơn vị thì báo "Chỉ nhập số, không ghi đơn vị"; sai dạng khác thì báo "Đáp số chưa đúng dạng số". Lỗi hiện ở dòng ghi chú cạnh nút Nộp, ô nhập có `aria-invalid`.
- CSS: thêm `.field-error` và viền `input[aria-invalid="true"]`, dùng token `--danger` sẵn có.

## Kiểm tra
- Web: tsc, eslint (các file đã sửa), vitest 19 file, 79/79. Test mới: `tests/login-survey-code.test.tsx`, `tests/answer-number.test.ts`.
- Trình duyệt local (dark mode), với khách mới:
  - Enter ở ô mã sai thì hiện lỗi cạnh ô nhập.
  - Chưa làm câu nào thì không hiện khung cảm ơn.
  - Nhập `17,3 triệu` thì báo lỗi đơn vị, nhập `17,3` thì nộp được và chấm đúng.
  - Làm xong 2/2 câu thì khung cảm ơn hiện ra.
- E2E Playwright **chưa chạy**.

## Chưa làm / cần người khác
- `NEXT_PUBLIC_SURVEY_URL` chưa đặt trên Vercel, nên nút "Mở phiếu khảo sát" không hiện. Cần đặt biến này rồi redeploy.
- Bài `dan-so-vung` trên production chỉ có 1 trong 4 dòng số liệu, do DB seed từ trước commit `aa6657a`. Đây là việc backend/dữ liệu.
- Góp ý UX nhỏ chưa làm:
  - Mọi trang có cùng tiêu đề "PreClass AI".
  - Thanh đầu trang dính cao 110px trên mobile.
  - Link "Quay lại" ở `/du-lieu` luôn về `/login`.
  - Hàng câu hỏi gợi ý HABIT bị cắt mà không có dấu hiệu cuộn ngang.
  - Câu trắc nghiệm chưa có `fieldset`/`legend`.
