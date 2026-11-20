# Habit: hướng thiết kế UI (S07)

Tham số design-taste-frontend: variance 4, motion 3, density 5. Công cụ học trên điện thoại, không phải landing page. **Không thêm thư viện**; chỉ CSS + token trong `apps/web/app/globals.css`.

**Nhân vật.** "Habit", xưng "Habit"–"em". Câu ngắn, khích lệ, không cợt nhả ("Em thử đọc lại đề nhé", "Habit không đưa đáp án — em tự làm nhé!"). Biểu tượng tự vẽ bằng SVG nội tuyến (vòng tròn + dấu sao 4 cánh, `currentColor`), không dùng ảnh hay nhân vật có bản quyền.

**Màu (token có sẵn).** Gợi ý/nút chính: `--primary` + `--info-bg` (teal). Từ chối/giới hạn: `--warning` + `--warning-bg` (vàng, không dùng đỏ). Nguồn trích: khung viền mảnh `--border` trên `--surface-2` + nhãn "Nguồn đã được thầy cô duyệt". Tiến độ: `.bar` hiện có (gradient teal–xanh lá, nhấn `--sun`). Cặp màu đều lấy từ token đã đạt tương phản AA ở cả sáng/tối.

**Chữ và khoảng cách.** Font hệ thống của app; nội dung chat 16px (≥16px trên 390 để iOS không phóng to khi nhập), nhãn nhỏ 13px chỉ cho chú thích. Khoảng cách theo bội số 4/8; nút và vùng bấm ≥ 44px.

**Trạng thái.** idle (ô nhập + 3 gợi ý nhanh) · đang trả lời ("Habit đang nghĩ…", `aria-busy`) · bị từ chối (vàng + câu mẫu) · lỗi mạng (đỏ nhạt của `alert-danger` + nút "Thử lại", dùng lại cùng `requestId`) · 429 (vàng: "Hôm nay em hỏi nhiều rồi, thử tự làm nhé!", ô nhập khóa) · hết thời gian 20 s coi như lỗi mạng.

**Chuyển động tối thiểu (CSS, ≤ 200 ms).** Bong bóng mờ-dần-và-trượt-4px khi xuất hiện; thanh mục tiêu/streak đầy dần (`width` transition). Tắt hoàn toàn dưới `prefers-reduced-motion` (đã có quy tắc chung ở cuối `globals.css`).

**Bố cục.**
- 390: `<dialog>` kiểu bottom-sheet, cao tối đa 75dvh, vùng nhập dính đáy, phần trên còn thấy câu hỏi; modal nên Esc đóng và focus bị giữ trong sheet.
- 768: bottom-sheet rộng tối đa 560px, căn giữa.
- 1280: panel phải 360px, **không modal** (`show()`), trang vẫn cuộn và nút Nộp vẫn bấm được; nội dung chính chừa lề phải 376px khi panel mở.
- Thanh Habit đầu trang: 🔥 streak · mục tiêu x/3 (thanh) · huy hiệu (biểu tượng + nhãn chữ, không chỉ màu).
- Mỗi câu: nút "Gợi ý 1/3" mở thẻ gợi ý ngay dưới câu hỏi; nút "Hỏi Habit" mở chat. Sau khi nộp: "Habit giải thích".

**A11y.** Phím Tab/Enter/Esc; `aria-live="polite"` cho vùng hội thoại; `role="status"` cho thông báo giới hạn; mọi nút có nhãn chữ; nội dung chat là văn bản thuần (không HTML/markdown).
