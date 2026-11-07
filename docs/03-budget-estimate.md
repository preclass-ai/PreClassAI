---
title: "03 — Dự toán chi phí — PreClass AI"
owner: "Khải (Tech/Dev Lead); phối hợp Mentor"
status: "Draft v0.4 — API AI + vận hành tối thiểu; chờ Mentor chốt trần"
last_reviewed: 2026-11-06
related: [Q-01, Q-02, 01, 02, 04, Tech Proposal v3.0]
---

# 03 — Dự toán chi phí

> **Nguyên tắc:** ưu tiên miễn phí nhưng phải ghi rõ các chi phí vận hành có thể phát sinh. API AI vẫn là khoản chính; VPS, domain, backup storage, điện/mạng dự phòng và công cụ trả phí là các khoản dự phòng, không được coi là chắc chắn bằng 0.
> **Đọc trước:** giá token là **giá tham chiếu quốc tế** *(nguồn)*; giá GreenNode/FPT cho từng model chỉ hiện trong console — **chưa xác minh**. **Tỷ giá:** 1 USD ≈ 26.000 VND. **Kỳ tính:** 06/11/2026 – 10/01/2027 (dev, eval, thực địa, 2 tháng vận hành).

## 1. Tổng hợp

| Kịch bản sử dụng | A — Gemma 4 31B-IT (VND) | B — Qwen 3.8 27B (VND) |
|---|---|---|
| Dev + eval (~100 ca × 4 cấu hình, chạy lại nhiều lần) | **0** (trong token miễn phí) | **0** (trong token miễn phí) |
| **80 HS nghiên cứu** (4 bài × 8 lượt) | **0** (trong token miễn phí) | **0** (trong token miễn phí) |
| 600 HS dùng thường xuyên (3 phiên/tuần × 6 lượt) | ~760.000 | ~2.460.000 |
| Trần lý thuyết: 1.000 HS dùng hết quota mỗi ngày | ~5.400.000 | ~15.000.000 |

Con số đã **trừ 100 triệu token miễn phí ban đầu** của FPT AI Factory *(nguồn)*. Nếu model được chọn không có trên FPT hoặc phải dùng GreenNode, xem số chưa trừ ở mục 2.2.

### 1.1 Kịch bản vận hành

| Kịch bản | Hạ tầng cố định dự kiến | Dự phòng 8,5 tuần | Điều kiện |
|---|---:|---:|---|
| Pilot desktop + Cloudflare Tunnel | 0 đ | 0–1.000.000 đ API | Chỉ mở dữ liệu thật khi có người trực, backup và restart plan |
| School/lab VM | 0 đ | 0–1.000.000 đ API | Có owner hạ tầng, điện/mạng và quyền vận hành |
| Vietnam VPS fallback | ~240.000 đ/tháng chưa VAT | 1.000.000 đ API + ~600.000 đ VPS cho 2,5 tháng | Mentor/nhà trường đứng tên thanh toán |
| GPU dedicated inference | Theo console/provider quote | Không dùng cho MVP | Chỉ xem xét khi load test chứng minh cần thiết |

**Khuyến nghị xin duyệt:** trần API 1.000.000 đ, cộng quỹ hạ tầng dự phòng tối đa 600.000 đ nếu không có VM miễn phí. Kill switch phải chuyển sang hint tĩnh trước khi chạm trần.

**Khuyến nghị:**
- **Phạm vi nghiên cứu (80 HS) và thi 20/11: 0 đồng** — dùng token miễn phí.
- Chọn **kịch bản A (Gemma 4)** trừ khi eval cho thấy Qwen tốt hơn rõ.
- Xin Mentor duyệt **trần API 1.000.000 đ** cho trường hợp mở rộng tới ~600 HS; nạp trước, app tự chuyển sang gợi ý tĩnh khi chạm ngân sách ngày.

## 2. Chi phí API AI

### 2.1 Giả định

| Giả định | Giá trị |
|---|---|
| Token mỗi lượt | ~2.500 vào (prompt hệ thống ~700, nguồn ~1.200, lịch sử ~400, bài + tin nhắn ~200), ~300 ra |
| Thinking mode | Tắt |
| Quota | 8 lượt/HS/ngày; ngân sách toàn hệ thống theo ngày |
| Thời gian vận hành | 8,5 tuần |
| Giá tham chiếu *(nguồn: FlexAI)* | Gemma 4 31B-IT: 0,14 / 0,40 USD; Qwen 3.8 27B: 0,20 / 2,50 USD mỗi 1 triệu token vào/ra |
| Token miễn phí | FPT AI Factory: tới 100 triệu token ban đầu *(nguồn)*; áp vào token đầu vào trước |

```
Chi phí API = max(0, token_vào − token_miễn_phí) × giá_vào + token_ra × giá_ra
```

### 2.2 Chi tiết theo kịch bản (chưa trừ / đã trừ token miễn phí)

| Kịch bản | Lượt AI | Token vào / ra | A chưa trừ | A đã trừ | B chưa trừ | B đã trừ |
|---|---|---|---|---|---|---|
| Dev + eval | ~2.000 | ~5M / 0,6M | ~25.000 | 0 | ~65.000 | 0 |
| 80 HS nghiên cứu | 2.560 | 6,4M / 0,8M | ~30.000 | 0 | ~75.000 | 0 |
| 600 HS | 91.800 | 230M / 27,5M | ~1.120.000 | ~760.000 | ~2.980.000 | ~2.460.000 |
| Trần 1.000 HS | 476.000 | 1,19B / 143M | ~5.800.000 | ~5.400.000 | ~15.500.000 | ~15.000.000 |

Dev + eval và 80 HS cộng lại ~11M token vào, vẫn trong 100M token miễn phí.

### 2.3 Cách giữ chi phí API ở mức 0 hoặc thấp nhất

| Biện pháp | Tác dụng |
|---|---|
| Dùng token miễn phí cho dev, eval, nghiên cứu | Chi phí phạm vi thi = 0 |
| Tắt thinking mode, `hint` ≤ 80 từ | Token đầu ra là khoản đắt nhất |
| Quota 8 lượt/HS/ngày, tối đa 6 lượt/câu | Chặn dùng lố |
| Ngân sách toàn hệ thống theo ngày + kill switch | Vượt ngưỡng → gợi ý tĩnh do GV soạn, 0 đ |
| Gợi ý tĩnh khi câu hỏi trùng mẫu đã có | Không gọi API cho câu lặp lại |
| Cắt lịch sử còn 4 lượt gần nhất | Giảm token đầu vào |
| Nạp trước theo trần đã duyệt | Không có hóa đơn bất ngờ |

## 3. Hạng mục không tính vào ngân sách — phương án miễn phí

| Hạng mục | Phương án miễn phí | Ghi chú |
|---|---|---|
| Máy chủ (prod + staging) | **Ưu tiên 1:** máy chủ/VM của Trường Lê Khiết. **Ưu tiên 2:** máy chủ lab đại học (cần thỏa thuận về dữ liệu). **Ưu tiên 3:** máy tính để bàn của trường chạy Docker + Cloudflare Tunnel (miễn phí) | Dữ liệu ở Việt Nam; xem file 04 mục 4 |
| Domain | Subdomain của trường, hoặc subdomain miễn phí của Cloudflare Tunnel (`*.trycloudflare.com` chỉ cho staging) | Không mua domain |
| HTTPS | Let's Encrypt qua Caddy, hoặc Cloudflare | |
| Backup | `pg_dump` mã hóa, chép sang ổ của trường hoặc Google Drive của nhà trường | Không dùng tài khoản cá nhân của HS |
| Repo, CI/CD, quản lý task | GitHub Free, GitHub Actions (2.000 phút/tháng), GitHub Projects | |
| Thiết kế | Figma Free/Education | |
| Kiểm thử | Playwright, axe, k6, điện thoại của thành viên | |
| Giám sát | Uptime Kuma tự host | |
| Bảo mật | gitleaks, Dependabot, `pnpm audit`, UFW, fail2ban | |
| Trợ lý code AI | Gói miễn phí hiện có của từng dev | Không mua thêm; không dán dữ liệu HS |
| Nhân sự | Tình nguyện | |

## 4. Hạng mục cần quyết định nếu không có phương án miễn phí

Không cộng vào tổng ở mục 1. Mentor/nhà trường quyết định có tài trợ hay không.

| Hạng mục | Khi nào cần | Mức tham khảo |
|---|---|---|
| Thuê VPS tại Việt Nam | Trường và lab đều không cấp máy chủ trước 09/11 | BizFly gói 2 vCPU/4 GB: 240.000 đ/tháng chưa VAT *(nguồn)* |
| Domain riêng | Trường không cho subdomain và cần URL ổn định cho phụ huynh | Vài trăm nghìn đ/năm *(ƯT)* |

## 5. Những gì chưa có trong dự toán

| Hạng mục | Lý do |
|---|---|
| In phiếu khảo sát, phiếu đồng ý, đề kiểm tra | Không thuộc chi phí sản phẩm |
| Thiết bị cho học sinh thiếu máy | Nhà trường bố trí |
| TTS/STT tiếng Việt | Ngoài phạm vi MVP |
| Tự host GPU | ~16 triệu đ/30 ngày *(nguồn)*, không phù hợp |

## 6. Task phát sinh

| ID | Task | Owner | Hạn |
|---|---|---|---|
| T3-01 | Đăng ký FPT AI Factory nhận token miễn phí; kiểm tra có Gemma 4 / Qwen 3.8 hoặc model tương đương | Khải | 06/11 |
| T3-02 | Lấy giá token + rate limit trên GreenNode và FPT (console) | Khải | 07/11 |
| T3-03 | Hỏi Mentor: trần API 1.000.000 đ và người đứng tên thanh toán (Q-01) | Khải | 07/11 |
| T3-04 | Hỏi Mentor/nhà trường về máy chủ miễn phí (file 04 mục 6.1) | Khải | 06/11 |
| T3-05 | Cấu hình quota, ngân sách ngày, kill switch | Khôi | 08/11 |
| T3-06 | Theo dõi token thật mỗi tuần từ `chat_turn`, so với token miễn phí còn lại | Khôi | từ 11/11 |

## 7. Nguồn tham khảo

- FPT AI Factory — Serverless inference FAQ, tính theo token, tới 100 triệu token miễn phí ban đầu: docs.fptcloud.com/docs/fpt-ai-factory/services/serverless-inference/faq/, factory.fpt.ai.
- GreenNode — Pricing, Model as a Service (1 credit = 1 đ; GPU instance từ 16.080.632 đ/30 ngày): greennode.ai/pricing.
- FlexAI — Pricing (giá tham chiếu Gemma 4 31B-IT, Qwen 3.8 27B): flex.ai/pricing.
- BizFly Cloud — Cloud VPS gói 4, 240.000 đ/tháng chưa VAT: bizflycloud.vn/cloud-vps (xem 04/11/2026).
