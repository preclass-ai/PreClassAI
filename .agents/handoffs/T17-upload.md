# Handoff: T17 — nạp giáo án nhiều định dạng

Status: `in_review` · Owner/harness: Claude Code · Date: 2026-11-21

## Skills đã dùng
| Skill | Bước | Kết quả |
|---|---|---|
| security-threat-model | trước khi code | `docs/security/THREAT-MODEL-upload.md` (13 mối đe dọa → biện pháp → test). Bước hỏi người dùng bỏ qua (chạy qua đêm). |
| security-best-practices | review code | Sửa: kiểm macro cho xlsm/pptm; chặn externalLinks/embeddings; `defusedxml`; chạy parser cách ly; nguồn FAILED không tạo bài. Còn: không quét mã độc. |
| design-taste-frontend | S01 | Vùng kéo-thả dùng token sẵn có, không thêm thư viện, CSS 160 ms. |
| web-design-guidelines | S01 | input file focusable (outline trên label), mục tiêu bấm ≥ 44 px, lỗi `role=alert`, văn bản tệp render thuần (test). |
| playwright-cli | E2E + ảnh | 390/768/1280/WebKit 8/8; xem ảnh. |

Chi tiết: `.agents/PR-upload.md`. Rủi ro: xem PR (RLIMIT_AS chưa thử trên Linux/Render).
