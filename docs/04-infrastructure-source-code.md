---
title: "04 — Source code, môi trường, hạ tầng và phương án tìm hạ tầng — PreClass AI"
owner: "Khải (Tech/Dev Lead); thực hiện chính: Khải + Khôi"
status: "Draft v0.2 — cập nhật đội (Khải, Khôi, Thiện; cố vấn EdTech chị Hiển, anh Khang)"
last_reviewed: 2026-11-06
related: [Q-01, Q-02, Q-07, ADR-0009, 03-budget-estimate]
---

# 04 — Source code, môi trường, hạ tầng

## 1. Quản lý và lưu trữ source code

### 1.1 Hiện trạng

Chưa có repo code. Đã có: 2 prototype trên `chatgpt.site` (PreClass AI demo, ThinkAI redesign), bộ tài liệu 01–06 của nhóm nội dung, Functional Specification ThinkAI v1.0 (28/10/2026), Tech Proposal v2 và Timeline (Claude Docs).

### 1.2 Đề xuất

| Hạng mục | Quyết định |
|---|---|
| Nền tảng | GitHub |
| Chủ sở hữu | **Tạo GitHub Organization** `preclass-ai`, không để repo dưới tài khoản cá nhân. Tối thiểu 2 owner kỹ thuật: Khải + Khôi. Mentor không cần quyền repo; giữ quyền billing và đứng tên tài khoản dịch vụ |
| Repo | `preclass-ai` (code + `docs/` + `content/`). Tài liệu nhóm nội dung (01–06) chuyển sang `docs/research/` dạng Markdown |
| Quyền | Team `leads` (admin: Khải); team `dev` (write: Khôi, Thiện); không cấp quyền repo cho thành viên không kỹ thuật: 2 HS chuyên Văn, Master Giáo dục làm trên bảng tính/Docs; chị Hiển, anh Khang góp ý trên staging và GitHub Issues (quyền triage nếu cần) |
| Branch | Trunk-based: `main` được bảo vệ (bắt buộc PR, 1 approval, CI xanh, không force push); nhánh ngắn `<ID>-<mo-ta>` theo ID trong Timeline (vd. `B4-revision-api`) |
| CODEOWNERS | `/apps/web/src/ai/**`, `/apps/web/src/core/**`, `/drizzle/**`, `/infra/**` → @Khải; `/apps/web/src/learning/**`, `/apps/web/src/teacher/**` → @Khôi; `/apps/web/app/**`, `/apps/web/src/ui/**` → @Thiện; `/content/**` → @Khôi (sinh từ bảng tính đã được GV duyệt) |
| Release | Tag `v1.0` (11/11), `v1.1` (18/11, bản thi); changelog sinh từ Conventional Commits |
| Bảo mật | 2FA bắt buộc; secret scanning + push protection; Dependabot; **không lưu dữ liệu học sinh thật trong repo, kể cả seed** — seed chỉ dùng mã mock `MOCK-01…30` |
| Sao lưu repo | Mirror hằng tuần sang GitLab private bằng GitHub Action |

## 2. Môi trường và hạ tầng build, phát triển

| Môi trường | Mục đích | Hạ tầng | Dữ liệu | Deploy |
|---|---|---|---|---|
| **local** | Dev code, debug | Máy cá nhân + `infra/compose.dev.yml` (Postgres 16) | Seed mock | Thủ công |
| **CI** | Lint, typecheck, test, build image | GitHub Actions; Testcontainers Postgres | Sinh tự động | Mỗi PR |
| **staging** | Test thiết bị, eval, chạy thử với HS | 05–09/11: máy của Khải chạy Docker + Cloudflare Tunnel (miễn phí); sau đó cùng máy chủ prod, Compose project `staging`, DB riêng, basic auth | **Chỉ dữ liệu mock** | Tự động khi merge `main` |
| **production** | Học sinh thật từ 11/11 | Máy chủ **miễn phí** tại Việt Nam (mục 4), tối thiểu 2 vCPU/4 GB, Compose project `prod` | Thật, đã có đồng ý | Thủ công có duyệt (GitHub Environment: Khải bấm duyệt) |

Staging và prod chạy chung một máy chủ để không phát sinh chi phí; cách ly bằng Compose project, mạng Docker, DB, secret và API key LLM khác nhau. Nếu k6 cho thấy staging ảnh hưởng prod thì tắt staging trong giờ học.

**Pipeline:**

```
PR ──▶ CI: install (pnpm cache) → lint → typecheck → unit → integration (Testcontainers) → build → gitleaks → audit
merge main ──▶ build image → push GHCR (tag sha) → deploy staging → smoke test → Playwright 3 viewport
tag v* ──▶ (duyệt) → pg_dump trước deploy → migrate → deploy prod → smoke test → báo nhóm Zalo
```

**Cách ly secret:** mỗi môi trường một bộ secret trong GitHub Environments. Staging dùng API key LLM riêng với trần thấp; không môi trường nào dùng chung mật khẩu DB hay khóa backup.

## 3. Quy mô tài nguyên cần thiết

### 3.1 Giả định tải (MVP, 11/11/2026 – 10/01/2027)

| Chỉ số | Giả định | Cơ sở |
|---|---|---|
| Tài khoản | 1.000 | Yêu cầu Dev Lead |
| Người dùng đồng thời | 100 cao điểm (tối trước tiết học) | Yêu cầu Dev Lead |
| Phiên | tối đa 1/HS/ngày, tối thiểu 2/tuần | Yêu cầu Dev Lead |
| Request web | ~10 req/s cao điểm (autosave 3 s, đọc trang) | Ước tính |
| Lượt AI | ~1 lượt/s cao điểm (100 HS × 8 lượt / 15 phút) | Ước tính; giới hạn thật là rate limit nhà cung cấp LLM |
| Dữ liệu | < 2 GB sau 2 tháng (chỉ văn bản) | 91.800 lượt × ~5 KB + bài làm |

### 3.2 Sizing

| Thành phần | Production | Staging |
|---|---|---|
| VM | 2 vCPU, 4 GB RAM, 40 GB SSD (chung VM) | Chung VM |
| Phân bổ RAM ước tính | Postgres 1 GB · web 1 GB · Caddy 0,1 GB · Uptime Kuma 0,2 GB · OS/dư 0,7 GB | web 0,5 GB · Postgres 0,5 GB |
| Backup ngoài | ~10 GB, khác máy, trong nước; giữ 14 bản (6 giờ/lần) + 4 bản tuần | Không backup |
| Băng thông | ≥ 100 Mbps | |
| OS | Ubuntu Server 24.04 LTS | |

**Tiêu chí nâng cấp:** CPU trung bình > 60% trong giờ cao điểm, RAM > 85%, disk > 70% hoặc p95 web > 2 s ở k6 → nâng gói 4 vCPU/8 GB (thao tác < 30 phút tại nhà cung cấp) hoặc tách staging sang VM khác.

## 4. Địa điểm triển khai sau khi hoàn thành

| Phương án | Ưu | Nhược | Điều kiện |
|---|---|---|---|
| **P1 — Máy chủ / VM của Trường Lê Khiết** | **0 đ**; dữ liệu nằm trong tổ chức trường | Thủ tục có thể chậm; có thể hạn chế root, mở port | VM hoặc máy để bàn có Docker, ≥ 2 vCPU/4 GB; IP public mở 80/443 hoặc dùng Cloudflare Tunnel |
| **P2 — Máy chủ lab đại học (URA, HCMUT)** | **0 đ**; có người vận hành | Dữ liệu trẻ em của trường khác trên hạ tầng đại học → cần thỏa thuận | Văn bản đồng ý của lab và Trường Lê Khiết |
| P3 — Máy tính để bàn (của trường hoặc thành viên) + Cloudflare Tunnel | **0 đ**; có ngay | Phụ thuộc điện, mạng, máy luôn bật; TLS kết thúc tại Cloudflare nên lưu lượng đi qua hạ tầng Cloudflare | Chỉ dùng cho staging hoặc phương án cuối cho buổi thực địa |
| P4 — Thuê VPS trong nước (BizFly, FPT Cloud, Viettel IDC, VNG Cloud) | Có ngay trong 1 giờ; ổn định | **Có phí** (~264.000 đ/tháng) — **ngoài ngân sách API**, chỉ dùng nếu Mentor/nhà trường tài trợ (file 03 mục 4) | Người đứng tên thanh toán không phải HS THPT |
| P5 — Cloud quốc tế / Vercel + Supabase | Nhanh, có free tier | Dữ liệu trẻ em ra nước ngoài → phát sinh hồ sơ đánh giá tác động chuyển dữ liệu xuyên biên giới (Luật 91/2025) | **Loại** cho mọi môi trường có dữ liệu thật |

**Khuyến nghị:** staging chạy P3 (máy của Khải + Cloudflare Tunnel, chỉ dữ liệu mock) ngay từ 06/11. Production: hỏi **P1** và **P2** song song ngay hôm nay; chốt trước **09/11**. Nếu cả hai không có, buổi 11/11 dùng P3 trên máy để bàn của trường và báo Mentor quyết định P4 (có phí, ngoài ngân sách API) cho giai đoạn sau. Không chuyển máy chủ giữa đợt nghiên cứu.

**Nguyên tắc bất kể phương án:** tài khoản hạ tầng, domain, LLM API và billing đứng tên **Mentor hoặc nhà trường**, không đứng tên học sinh THPT. Khi đội rời dự án, người phụ trách vẫn kiểm soát được hệ thống và dữ liệu.

## 5. Domain

| Câu hỏi cần trả lời | Hỏi ai | Ảnh hưởng |
|---|---|---|
| Trường có cho dùng subdomain (vd. `preclass.<domain-truong>`)? (Q-07) | Mentor → nhà trường | Uy tín với phụ huynh; 0 đ |
| Nếu không, mua domain mới đứng tên ai? | Mentor | Không đứng tên HS THPT |
| Ai giữ quyền DNS? | Mentor | Cần bản ghi A/CNAME |

**Phương án đề xuất:**

1. Ưu tiên subdomain của trường (0 đ). Nếu chưa có trước 09/11: dùng subdomain miễn phí của Cloudflare Tunnel; không mua domain.
2. Staging dùng `staging.<domain>` có basic auth và `noindex`.
3. Cloudflare Free trước Caddy nếu chủ domain đồng ý (WAF, DDoS cơ bản).

## 6. Phương án tìm kiếm hạ tầng

### 6.1 Nhà trường (qua Mentor)

**Nội dung cần hỏi:**

1. Trường có thể cấp VM cho đề tài không? Thủ tục, thời gian, người phê duyệt?
2. Có dùng subdomain của trường được không?
3. Ai là người chịu trách nhiệm dữ liệu học sinh của đề tài (Q-08)?
4. Mạng Wi-Fi phòng thực địa 11/11 có chặn domain mới hoặc cổng 443 lạ không (Q-05)?
5. Có danh sách mã HS (không họ tên) cho lớp tham gia trước 10/11 không (Q-04)?

### 6.2 Nhà cung cấp LLM (Khải)

1. Giá token vào/ra của Qwen 3.8 27B, Gemma 4 31B-IT (self-hosted).
2. Rate limit theo key (request/phút, token/phút).
3. Vùng xử lý cụ thể (HCM/HAN hay có Bangkok) và có ghim vùng được không.
4. Cam kết không dùng prompt/response để huấn luyện; thời gian lưu log.
5. Hóa đơn VAT, nạp trước, cảnh báo khi gần hết credit.

### 6.3 Tiêu chí chọn nhà cung cấp VPS (chỉ khi phải dùng P4)

| Tiêu chí | Trọng số |
|---|---|
| Data center tại Việt Nam | Bắt buộc |
| Gói 2 vCPU/4 GB, nâng cấp tại chỗ | Bắt buộc |
| Snapshot/backup | Cao |
| Thanh toán theo tháng, có hóa đơn | Cao |
| Giá / tháng | Trung bình |
| Hỗ trợ tiếng Việt 24/7 | Trung bình |

Ứng viên: BizFly Cloud (đã có giá công khai 240.000 đ/tháng chưa VAT), FPT Cloud, Viettel IDC, VNG Cloud.

## 6b. Tái sử dụng code và dữ liệu cũ

### 6b.1 Tài sản cần kiểm kê

| Tài sản | Câu hỏi | Nguồn thông tin |
|---|---|---|
| Prototype PreClass AI demo (`chatgpt.site`) | Có source không? Stack gì? Phần giao diện nào cần giữ? | chị Hiển |
| Prototype ThinkAI redesign | Như trên; luồng nào khác PreClass hiện tại? | chị Hiển, anh Khang |
| Functional Spec ThinkAI v1.0 | Phần nào còn đúng sau khi đổi sang Ngữ văn + H.A.B.I.T? | Khải |
| Tài liệu 01–06 nhóm nội dung | Gói L1–L4, câu T, rubric, phiếu khảo sát | 2 HS chuyên Văn, Master Giáo dục |
| Dữ liệu học sinh cũ | Có dữ liệu nào từ ThinkAI pilot không? | Mentor |

### 6b.2 Tiêu chí quyết định tái sử dụng

| Tiêu chí | Tái sử dụng nếu… | Không tái sử dụng nếu… |
|---|---|---|
| Code | Cùng stack (TS/React/Next.js), có source, có người hiểu | Sinh tự động không có source, không có test |
| Nội dung | Giáo viên xác nhận còn đúng | Thuộc ThinkAI Địa lí cũ |
| Dữ liệu học sinh | Có đồng ý cho mục đích mới | Không rõ nguồn → **không nhập**; tài liệu 05 nhóm nội dung cấm dùng số liệu ThinkAI cũ cho PreClass |

### 6b.3 Kết luận dự kiến

- **Code prototype:** không tái sử dụng code; tái sử dụng **luồng màn hình, câu chữ giao diện, bố cục** làm tham chiếu cho Thiện.
- **Tài liệu:** chuyển vào `docs/`; gói L1–L4 chuyển thành `content/lessons/*.json`.
- **Dữ liệu:** không nhập dữ liệu nào từ ThinkAI.

| ID | Task | Owner | Hạn |
|---|---|---|---|
| T4-07 | Kiểm kê tài sản mục 6b.1, chụp màn hình prototype vào `docs/reference/` | Thiện | 06/11 |
| T4-08 | Chuyển gói L1 từ tài liệu 03 nhóm nội dung sang `content/lessons/L1.json` | Khôi + 2 HS chuyên Văn | 06/11 12:00 |

## 7. Mốc quyết định

| Ngày | Mốc | Nếu trễ |
|---|---|---|
| 06/11 | GitHub Org, repo, CI chạy; staging qua Cloudflare Tunnel có HTTPS | Chặn toàn bộ dev |
| 09/11 | Có máy chủ production miễn phí (P1 hoặc P2) | Dùng P3 cho 11/11; Mentor quyết định P4 |
| 07/11 | Có giá token + rate limit LLM (T3-01) | Dùng FPT free token cho eval; chọn model theo chất lượng trước |
| 08/11 | Có trần ngân sách và người đứng tên (Q-01) | Bật `ai.enabled` chỉ cho 80 HS nghiên cứu |
| 09/11 | Backup đã khôi phục thử; k6 100 người ảo đạt | Không mở prod cho học sinh thật |
| 10/11 | Domain chính thức (Q-07); danh sách mã HS (Q-04) | Dùng domain tạm + tài khoản mock |

## 8. Task phát sinh

| ID | Task | Owner | Hạn |
|---|---|---|---|
| T4-01 | Tạo GitHub Org, repo, team, branch protection, 2FA, CODEOWNERS | Khải | 06/11 |
| T4-02 | Gửi Mentor 5 câu hỏi mục 6.1 | Khải | 06/11 |
| T4-03 | Hỏi nhà cung cấp LLM 5 câu mục 6.2 | Khải | 07/11 |
| T4-04 | Pipeline CI/CD theo mục 2 | Khải | 06/11 |
| T4-05 | Script provisioning máy chủ (Ubuntu hardening, Docker, Caddy, UFW, fail2ban) chạy được trên P1–P4 | Khải | 06/11 |
| T4-06 | Script backup + restore, diễn tập khôi phục sang máy mới | Khôi | 09/11 |
