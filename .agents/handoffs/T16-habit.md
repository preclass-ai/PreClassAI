# Handoff: T16 — Habit (chat + thói quen học)

Status: `in_review` · Owner/harness: Claude Code · Date: 2026-11-21

## Skills đã dùng
| Skill | Bước | Kết quả |
|---|---|---|
| security-threat-model | trước khi code | `docs/security/THREAT-MODEL-habit.md` (16 mối đe dọa → biện pháp → test). Bước hỏi người dùng bỏ qua (chạy qua đêm), giả định ghi sẵn. |
| design-taste-frontend (variance 4, motion 3, density 5) | thiết kế UI | `docs/ui/HABIT-DESIGN.md`; không thêm thư viện; token sẵn có; CSS ≤ 200 ms + reduced-motion. |
| web-design-guidelines | sau UI | Không có lỗi Chặn/Cao. Sửa: placeholder "…", autocomplete off, overscroll-behavior, touch-action, safe-area, hover. Còn: transition `width` của thanh mục tiêu (mẫu `.bar` sẵn có). |
| vercel-react-best-practices | cấu trúc chat | Chat `next/dynamic` lazy, state chat cục bộ từng câu, không waterfall. |
| security-best-practices | review Python/TS | Sửa: học sinh phá khung `<student_message>` (defang `<` `>`); regex địa chỉ nuốt "phương án"; guard thiếu "đáp án là A". |
| playwright-cli / playwright | E2E + ảnh | 390/768/1280/WebKit xanh; xem ảnh, sửa nút Gửi bị kéo giãn và cuộn lệch ở WebKit. |

## Interfaces
`docs/api/API_GUIDE.md` mục 12, `DATA_MODEL.md` (migration 0003), `.agents/PR-habit.md`.

## Risks / next
LLM mode chưa thử model thật; bật cần ADR/đồng ý của trường. Phần 2 (personalization) dựng trên nhánh này.
