---
title: "06 — MVP scope và Master plan — PreClass AI"
owner: "Khải (Tech Lead); góp ý: chị Hiển, anh Khang; Mentor đồng duyệt"
status: "Draft v0.2 — cập nhật đội (Khải, Khôi, Thiện; cố vấn EdTech chị Hiển, anh Khang) — khung để Mentor duyệt"
last_reviewed: 2026-11-06
related: [01, 05, Tech Proposal v2, Timeline (Claude Docs), tài liệu 05 nhóm nội dung]
---
> **Superseded by [ADR-0010](adr/ADR-0010-fastapi-backend.md) / D-001 (2026-11-14).** Tài liệu này mô tả thiết kế cũ (Next.js full-stack, H.A.B.I.T, Ngữ văn). Giữ để tham khảo; không làm theo phần kiến trúc/API/phạm vi. Hướng hiện hành: `docs/v2/`.


# 06 — MVP scope và Master plan

> Tài liệu này là **bản đề xuất** để chốt phạm vi MVP. Khi Mentor xác nhận, đổi status thành Accepted và ghi ngày, người xác nhận.

## 1. MVP — đề xuất phạm vi

**Mục tiêu MVP:** đến 10/11/2026, học sinh lớp 10 Lê Khiết **đi hết được** một nhiệm vụ chuẩn bị bài Ngữ văn theo H.A.B.I.T trên điện thoại, tablet hoặc laptop; AI chỉ gợi ý có nguồn và không làm hộ; giáo viên **xem được** tiến độ và chỗ vướng của lớp.

| Phân hệ | Trong MVP (10/11) | Không trong MVP (sau 11/11) |
|---|---|---|
| Tài khoản | Đăng nhập mã HS, đổi mật khẩu lần đầu, GV reset mật khẩu, nhập CSV | SSO Google Workspace của trường |
| Gói bài | L1 (L2 nếu kịp), nạp từ JSON | L3–L4 (trước tuần 3–4), T02 soạn bài trên giao diện |
| Không gian học S03 | H, A (chọn đoạn), B0 bất biến, Bn, autosave, ghi chú riêng trên thiết bị, 3 breakpoint | PWA, offline đầy đủ |
| AI tutor | 6 mục đích (cắt còn 3 nếu trễ), gợi ý có nguồn, guardrail bằng code, hint tĩnh, kill switch, quota | Hint thích ứng theo năng lực, moderation nâng cao |
| Bước T | T1 → T2, AI khóa ở máy chủ, nộp kèm chỗ vướng | Kho câu T > 2/bài |
| Giáo viên | T01 tổng quan lớp, T04 xem bài B0→Bn + chat, chỗ vướng, khóa báo cáo nghiên cứu | T05 hàng đợi đầy đủ, nhập điểm, xuất dữ liệu (R01) |
| Đánh giá AI | Eval ~100 ca, 2 GV chấm, κ | Kiểm toán 100 hội thoại thật |

**Điều kiện mở cho học sinh thật:** Q-03 (phiếu đồng ý) đã thu cho học sinh tham gia; backup đã khôi phục thử; eval có 0 ca lộ đáp án trong 20 ca xin viết hộ. Nếu chưa đạt vào 10/11: buổi 11/11 chạy **thử luồng trên tài khoản mock** với học sinh đã đồng ý quan sát, không thu dữ liệu nghiên cứu.

## 2. Master plan

### 2.1 Các giai đoạn

| Giai đoạn | Thời gian | Kết quả |
|---|---|---|
| **G0 — Khởi động** | 05–06/11 | Tài liệu 01–07, repo + CI, staging miễn phí, schema, mẫu gói bài |
| **G1 — Xây dựng** | 06–09/11 | S01–S04, AI tutor, bước T, dashboard GV; freeze 09/11 21:00 |
| **G2 — Nghiệm thu** | 10/11 | Chạy thử 3–5 HS, Go/No-go, tag `v1.0` |
| **G3 — Thực địa buổi 1** | 11/11 | Khảo sát (tài liệu 02 nhóm nội dung), thử luồng 8–12 HS, trực sự cố |
| **G4 — Sửa theo phản hồi** | 12–18/11 | Tối đa 2 vòng sửa, L2 sẵn sàng, buổi 2 (~18/11), tag `v1.1` |
| **G5 — Thi** | 19–20/11 | Tổng duyệt 19/11, thi 20/11: trình bày protocol + số liệu khả thi + dữ liệu quá trình |
| **G6 — Nghiên cứu tiếp** | 21/11 – 10/01 | L3–L4, hậu kiểm ~02/12, ANCOVA ~09/12, kiểm toán hội thoại |

### 2.2 Milestone

| Mã | Milestone | Ngày | Tiêu chí đạt | Chủ |
|---|---|---|---|---|
| M0 | Phạm vi MVP + vai trò chốt | 06/11 | Tài liệu 05, 06 được Mentor xác nhận | Khải |
| M1 | Khung chạy được | 06/11 | Staging HTTPS qua Cloudflare Tunnel; đăng nhập mock; thấy L1 | Khải, Khôi |
| M2 | Luồng tự làm | 07/11 | H→A→B0→Bn lưu được trên 390 px; eval chạy lần 1; chị Hiển, anh Khang góp ý UX trên staging | Thiện, Khôi |
| M3 | AI hoàn chỉnh | 08/11 | Chat + guardrail + hint tĩnh; model chọn xong; T khóa AI | Khải |
| M4 | Freeze | 09/11 21:00 | Dashboard GV; k6 100 người ảo; backup đã khôi phục thử | Cả team |
| M5 | Go/No-go | 10/11 20:00 | AC chặn đạt; 3–5 HS chạy thử; Q-03 có kết quả | Khải, Mentor |
| M6 | Thực địa buổi 1 | 11/11 | Nhật ký sự cố + số liệu khả thi | Cả team |
| M7 | Bản thi | 18/11 | Tag `v1.1`, video demo dự phòng | Khải |
| M8 | Thi | 20/11 | | Nhóm |
| M9 | Kết quả nghiên cứu | ~09/12 | Chênh lệch hậu kiểm + CI 95% | Master Giáo dục |

### 2.3 Lịch theo stream (theo ngày)

| Stream | 05/11 | 06/11 | 07/11 | 08/11 | 09/11 | 10/11 | 11/11 | 12–18/11 |
|---|---|---|---|---|---|---|---|---|
| Platform | Repo, CI | Staging, schema, auth; hỏi máy chủ trường | Access, test quyền | Quota, budget | Backup, k6 | Go/No-go | Trực | Sửa lỗi |
| Học sinh (S) | Tokens | Layout 3 breakpoint, S01–S02 | S03 H/A/B | UI chat, bước T | S04, test máy thật | Chạy thử | **M6** | Sửa UX |
| AI tutor | LLM key | `/api/chat`, hint tĩnh | Guardrail, eval lần 1 | **Chọn model** | Prompt v1 freeze | | Theo dõi | Kiểm toán mẫu |
| Giáo viên (T) | | | API progress | T01/T04 | Khóa báo cáo | | | T05 |
| Nội dung | Bảng tính mẫu | **L1 12:00**, 100 ca | GV chấm eval | GV chấm xong | L2 | Phiếu đồng ý | Khảo sát | L3 |

Freeze tính năng 09/11 21:00; ngày 10/11 chỉ sửa lỗi.

## 3. Rủi ro chính của master plan

| Rủi ro | Dấu hiệu sớm | Phương án |
|---|---|---|
| Gói L1 trễ | 06/11 12:00 chưa có JSON hợp lệ | Code bằng L0 mẫu; hint tĩnh viết tạm, GV duyệt sau |
| AI chưa đạt eval | 08/11 còn ca lộ đáp án | Tắt LLM, chạy hint tĩnh cho buổi 1 |
| Rate limit LLM thấp | k6 09/11 có 429 | FPT dự phòng; hàng đợi + thông báo chờ |
| Giờ công thấp (3 giờ/ngày) | 07/11 tối chưa đạt M2 | Cắt theo thứ tự trong Timeline: T01/T04 → 3 mục đích → kiểm trích dẫn → tablet dùng layout laptop |
| Chưa có phiếu đồng ý | 10/11 chưa thu | Buổi 1 chỉ thử luồng bằng tài khoản mock |
| Kỳ vọng kết quả hiệu quả tại 20/11 | — | Trình bày protocol + khả thi; kết quả nhân quả ~09/12 |

## 4. Task phát sinh

| ID | Task | Owner | Hạn |
|---|---|---|---|
| T6-01 | Đồng bộ master plan với tab Timeline (Claude Docs) và GitHub Projects | Khải | 06/11 |
| T6-02 | Trình phạm vi MVP cho Mentor, xin xác nhận | Khải | 06/11 |
| T6-03 | Đăng ký trước thiết kế nghiên cứu (OSF hoặc tài liệu có dấu thời gian) | Master Giáo dục | 10/11 |
| T6-04 | Kịch bản demo 5 phút + video dự phòng | chị Hiển, anh Khang (kịch bản); Khải, Thiện (quay) | 18/11 |
