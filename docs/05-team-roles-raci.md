---
title: "05 — Phân công vai trò, RACI và thứ tự ưu tiên — PreClass AI"
owner: "Khải (Tech/Dev Lead); góp ý: chị Hiển, anh Khang"
status: "Draft v0.2 — cập nhật đội (Khải, Khôi, Thiện; cố vấn EdTech chị Hiển, anh Khang)"
last_reviewed: 2026-11-06
related: [01, 02, 03, 04, 06-master-plan-mvp, 07-recruitment-plan]
---
> **Superseded by [ADR-0010](adr/ADR-0010-fastapi-backend.md) / D-001 (2026-11-14).** Tài liệu này mô tả thiết kế cũ (Next.js full-stack, H.A.B.I.T, Ngữ văn). Giữ để tham khảo; không làm theo phần kiến trúc/API/phạm vi. Hướng hiện hành: `docs/v2/`.


# 05 — Phân công vai trò, RACI và thứ tự ưu tiên

## 1. Cơ cấu đội

Đội nền **9 người** ở 4 nhóm. Chỉ nhóm Dev có chuyên môn kỹ thuật; các nhóm còn lại góp ý sản phẩm, sư phạm và nội dung, **không được giao việc cần code, terminal hay cấu hình hệ thống**.

| Nhóm | Thành phần | Hiện có | Cần bổ sung |
|---|---|---|---|
| **Dev chính** | Tech Lead, Backend, Frontend | Khải, Khôi, Thiện | 0 |
| **Cố vấn EdTech** | Góp ý sản phẩm, UX học tập, câu chuyện sản phẩm | chị Hiển, anh Khang | 0 |
| **Sư phạm & nội dung** | Master Giáo dục; 2 HS chuyên Văn | Đủ | 1 GV Ngữ văn thứ hai để chấm eval độc lập (file 07) |
| **Điều phối** | Mentor của 2 HS | Mentor | 0 |
| **Kiểm thử** | Tester trên thiết bị thật | Chưa có | 1–2 tình nguyện viên (file 07) |
| **Tổng** | | **9** | **2–3** |

GV Ngữ văn của trường duyệt nội dung bài học nhưng là **bên liên quan**, không thuộc đội.

```
                 ┌──────────────────────────────────────────────────┐
                 │ CHUNG: GIẢI PHÁP, SẢN PHẨM & SƯ PHẠM              │
                 │ Kỹ thuật: Khải · Sản phẩm/UX học tập: chị Hiển,   │
                 │ anh Khang · Sư phạm, nghiên cứu: Master Giáo dục  │
                 └──────────────────────┬───────────────────────────┘
   ┌───────────────┬────────────────────┼────────────────────┬────────────────┐
┌──▼───────────┐ ┌─▼─────────────┐ ┌────▼────────────┐ ┌──────▼──────┐ ┌───────▼───────┐
│ PLATFORM     │ │ HỌC SINH (S)  │ │ AI TUTOR        │ │ GIÁO VIÊN(T)│ │ NỘI DUNG      │
│ Khải, Khôi   │ │ Thiện (lead)  │ │ Khải (lead)     │ │ Khôi (API)  │ │ 2 HS Văn      │
│ repo, server,│ │ Khôi (API)    │ │ Khôi (quota)    │ │ Thiện (UI)  │ │ + Mentor      │
│ auth, DB     │ │ S01–S04       │ │ eval: Master GD │ │ T01/T04/T05 │ │ GV duyệt      │
│              │ │ góp ý: Hiển,  │ │ góp ý: Hiển,    │ │ góp ý:      │ │ (bảng tính,   │
│              │ │ Khang         │ │ Khang           │ │ Khang       │ │ không JSON)   │
└──────────────┘ └───────────────┘ └─────────────────┘ └─────────────┘ └───────────────┘
   Ưu tiên 1         Ưu tiên 1          Ưu tiên 2          Ưu tiên 3        Ưu tiên 1
```

**Khôi chia thời gian:** 05–07/11 làm Platform cùng Khải (schema, auth); từ 07/11 chuyển sang API học sinh và giáo viên. Mục đích: có 2 người hiểu phần lõi.

> Giả định phân vai: **Khôi = Backend, Thiện = Frontend**. Nếu ngược lại, đổi tên trong mục 2, mục 3 và các bảng task của file 01–07.

## 2. Vai trò

| Vai trò | Người | Trách nhiệm | Được quyết | Không tự quyết |
|---|---|---|---|---|
| **Tech/Dev Lead** | Khải | Xếp ưu tiên module; chọn stack; kiến trúc, ADR; pipeline AI + guardrail + eval; review mọi PR chạm auth/ai/migration; hạ tầng; Go/No-go kỹ thuật | Kiến trúc, stack, chuẩn code, model LLM (theo eval), Go/No-go kỹ thuật | Nội dung bài học, thiết kế nghiên cứu, ngày thực địa |
| **Dev Backend** | Khôi | Schema, migration, auth, access, API phiên/bài làm/nộp/bước T, quota, dashboard API, backup; chuyển bảng tính nội dung thành JSON | Thiết kế bên trong module `learning`, `teacher` | Đổi schema chung, auth, cấu trúc AI |
| **Dev Frontend** | Thiện | Design tokens, layout 3 breakpoint, S01–S04, UI chat, T01/T04, test thiết bị | Component, bố cục, câu chữ giao diện (sau khi cố vấn EdTech và nhóm nội dung xem) | Đổi luồng H.A.B.I.T |
| **Cố vấn EdTech** | chị Hiển, anh Khang | Góp ý luồng học sinh và giáo viên, câu chữ giao diện, dashboard "chỗ vướng", câu chuyện sản phẩm và kịch bản demo; xem staging ở các mốc M2, M3, M5 | Đề xuất thay đổi UX, ưu tiên tính năng trình bày với giám khảo | Stack, kiến trúc, quyết định kỹ thuật; thêm tính năng sau freeze 09/11 |
| **Master Giáo dục** | Master Giáo dục | Phản biện H.A.B.I.T, chính sách AI, thiết kế nghiên cứu; duyệt rubric eval; chấm eval | Tiêu chí sư phạm, rubric, thiết kế nghiên cứu | Stack, model |
| **Mentor** | Mentor của 2 HS | Hướng dẫn 2 HS; đầu mối với nhà trường; ngân sách; đứng tên thanh toán và tài khoản dịch vụ; phiếu đồng ý; lịch thực địa | Ngân sách, lịch với trường | Mọi việc kỹ thuật (không cần quyền truy cập máy chủ hay repo code) |
| **Nội dung** | 2 HS chuyên Văn | Gói bài L1–L2 (nguồn, câu hỏi, đáp án mẫu, hint 3 mức, hiểu lầm, câu T) **trên bảng tính mẫu**; viết 100 ca eval; thử luồng như người dùng | Cách diễn đạt gói bài, ca eval | Tự đặt đáp án khi GV chưa duyệt |
| **GV Ngữ văn** (bên liên quan) | GV của trường (×2) | Duyệt gói bài; chấm eval độc lập; dùng dashboard | Duyệt/không duyệt nội dung | — |
| **Tester** (tình nguyện) | Tuyển (file 07) | Chạy kịch bản test trên máy thật; ghi lỗi có ảnh | Đánh mức nghiêm trọng | Bỏ qua lỗi chặn để kịp hạn |

### 2.1 Thành viên không có chuyên môn kỹ thuật — cách làm việc

| Biện pháp | Chi tiết |
|---|---|
| Không dùng công cụ dev | 2 HS chuyên Văn và Mentor làm trên Google Sheets/Docs mẫu (một dòng = một câu hỏi, cột cho nguồn, đáp án mẫu, hint 1–3, hiểu lầm, câu T). Khôi viết script chuyển bảng tính → `content/lessons/L{n}.json` và báo lỗi bằng tiếng Việt |
| Cổng kiểm tra | Mọi gói bài qua GV duyệt trước, Khải xác nhận "đủ để seed" |
| Góp ý có cấu trúc | Cố vấn EdTech góp ý trực tiếp trên staging bằng form 3 cột (màn hình · vấn đề · đề xuất); Khải phân loại "làm trước freeze / sau thực địa / không làm" trong 24 giờ |
| Phạm vi phù hợp | Giao: nội dung, hint, câu T, ca eval, góp ý UX, kịch bản demo. Không giao: sửa code, cấu hình prompt, quyền máy chủ |
| Không chặn dev | Khôi dùng gói L0 mẫu để code trong lúc chờ L1 |

## 3. Ma trận RACI

R = thực hiện · A = chịu trách nhiệm cuối (một A mỗi dòng) · C = tham vấn · I = thông báo

| Hoạt động | Khải | Khôi | Thiện | Hiển, Khang | Master GD | Mentor | HS Văn ×2 | GV | Tester |
|---|---|---|---|---|---|---|---|---|---|
| Chốt phạm vi MVP 11/11 | **A/R** | C | C | C | C | C | I | I | I |
| Xếp ưu tiên module, stack | **A/R** | C | C | C | I | I | I | I | I |
| Kiến trúc, ADR, ERD (doc 01, 02) | **A/R** | R | C | I | C | I | I | I | I |
| Dự toán chi phí (doc 03) | **A/R** | I | I | I | I | C | I | I | I |
| Ngân sách, người đứng tên tài khoản | C | I | I | I | I | **A/R** | I | I | I |
| Hạ tầng, source code (doc 04) | **A/R** | R | I | I | I | I | I | I | I |
| Platform: auth, access, schema | **A** | R | C | I | I | I | I | I | C |
| S01–S04 giao diện học sinh | C | C | **A/R** | C | C | I | C | I | R |
| H.A.B.I.T state machine | **A** | R | C | C | C | I | I | I | C |
| Pipeline AI + guardrail | **A/R** | C | I | C | C | I | I | I | I |
| Gói bài L1–L2 (bảng tính → JSON) | C | R | I | I | C | C | **R** | **A** | I |
| Eval 100 ca: viết ca | C | I | I | C | C | I | **A/R** | C | I |
| Eval: chấm, tính κ, chọn model | **A** | I | I | I | R | I | C | R | I |
| Dashboard giáo viên | C | R | **A/R** | C | C | I | I | C | R |
| Câu chuyện sản phẩm, kịch bản demo | C | I | R | **A/R** | C | C | C | I | I |
| Phiếu đồng ý, đăng ký trước nghiên cứu | C | I | I | I | R | **A/R** | I | C | I |
| Test thiết bị thật, test quyền | C | R | **A** | I | I | I | R | I | R |
| Go/No-go 10/11 | **A** | C | C | C | C | C | C | C | R |
| Deploy production | **A/R** | C | I | I | I | I | I | I | I |
| Trực sự cố 11/11 và vận hành 2 tháng | **A** | R | R | I | I | I | I | I | I |

## 4. Thứ tự ưu tiên module (Tech Lead xếp)

| Ưu tiên | Module | Lý do | Mốc |
|---|---|---|---|
| **1** | Platform: repo, CI, máy chủ, schema, auth | Mọi module phụ thuộc | 06/11 |
| **1** | S03 bài làm H→A→B0→Bn, autosave | Lõi sư phạm; chạy được kể cả khi tắt AI | 07/11 |
| 1 (song song) | Gói L1 + 100 ca eval | AI và seed phụ thuộc | 06/11 |
| **2** | AI tutor: chat, guardrail, hint tĩnh, bước T | Bước I và T | 08/11 |
| **3** | Dashboard giáo viên T01/T04, khóa báo cáo | Cần dữ liệu phiên | 09/11 |
| 4 | Backup, k6, test thiết bị, freeze | | 09–10/11 |

**Định nghĩa "S03 xong":** đi hết H→A→B0→I→T→Nộp trên điện thoại 390 px không cần người hướng dẫn; tải lại trang không mất bài; B0 không sửa được; gọi API chat khi ở T trả 409; Lighthouse mobile ≥ 85.

## 5. Nhịp phối hợp

| Hoạt động | Chủ trì | Khi nào |
|---|---|---|
| Standup tối (15 phút, có thể async trên Zalo) | Khải | Hằng ngày 05–19/11 |
| Design review | Khải | Khi đổi schema, auth, prompt |
| Review PR | Khải (core, ai, migration); Khôi ↔ Thiện review chéo phần còn lại | Trong 4 giờ |
| Sync nội dung ↔ dev | 2 HS chuyên Văn + Khôi | 06/11 sáng, 08/11 tối |
| Chấm eval | GV + Master Giáo dục | 07/11 tối – 08/11 12:00 |
| Demo staging cho cố vấn EdTech, Mentor và GV | Khải | 07/11 tối (M2), 08/11 tối (M3), 10/11 (M5) |
| Phiên góp ý EdTech (form 3 cột) | chị Hiển, anh Khang | Sau mỗi buổi demo staging |
| Go/No-go | Khải | 10/11 20:00 |

## 6. Quy tắc chống "mỗi người tự thiết kế một phần"

1. Không ai tự tạo bảng DB, endpoint, thư viện mới ngoài ERD / OpenAPI / ADR. Muốn thêm → issue `design-change`, Khải duyệt trong 4 giờ.
2. Zod schema + OpenAPI trước, code sau.
3. Một state machine H.A.B.I.T ở máy chủ; giao diện không tự mở/đóng bước.
4. Mọi thay đổi prompt phải chạy lại eval trước khi merge.
5. Nhóm nội dung không tự đặt đáp án khi GV chưa duyệt; chỗ chưa rõ ghi Q-xx.

## 7. Task phát sinh

| ID | Task | Owner | Hạn |
|---|---|---|---|
| T5-01 | Kickoff: trình bày tài liệu 01–07, xác nhận vai trò | Khải | 06/11 |
| T5-02 | Lấy tài khoản GitHub của Khôi, Thiện; chia quyền xem staging cho chị Hiển, anh Khang, Master GD | Khải | 06/11 |
| T5-03 | Board Timeline trên GitHub Projects theo ID task | Khải | 06/11 |
| T5-04 | Gửi bảng tính mẫu + hướng dẫn cho nhóm nội dung; script chuyển sang JSON | Khôi | 06/11 09:00 |
| T5-05 | Mời GV Ngữ văn thứ hai chấm eval (file 07) | Mentor | 07/11 |
| T5-06 | Chốt lịch trực sự cố 11/11 – 10/01 | Khải | 10/11 |
