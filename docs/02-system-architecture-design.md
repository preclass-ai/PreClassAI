---
title: "02 — Thiết kế kiến trúc & phát triển hệ thống — PreClass AI"
owner: "Khải (Tech/Dev Lead)"
status: "Draft v0.2 — cập nhật đội (Khải, Khôi, Thiện; cố vấn EdTech chị Hiển, anh Khang)"
last_reviewed: 2026-11-06
related: [01-architecture-overview-adr-erd, 04-infrastructure-source-code, ADR-0001..0009]
---

# 02 — Thiết kế kiến trúc & phát triển hệ thống

> **Mục tiêu tài liệu:** 3 dev bắt đầu code trên **một** kiến trúc chung, không ai tự thiết kế phần riêng rồi ghép sau.
> Tài liệu 01 trả lời *hệ thống là gì và vì sao*. Tài liệu này trả lời *xây như thế nào*: stack, cấu trúc code, luồng dữ liệu, API, AI, bảo mật, công cụ.

---

## 1. Kiến trúc tổng thể và cấu trúc thành phần

### 1.1 Kiểu kiến trúc

**Next.js full-stack monolith** (ADR-0001): một ứng dụng Next.js chứa cả giao diện và API (Route Handlers), chung một PostgreSQL, chạy bằng Docker Compose trên một máy chủ miễn phí tại Việt Nam (file 04 mục 4). Lý do: 3 dev, 4 ngày đến freeze 09/11, tải thấp (100 người cùng lúc).

```
┌──────────────── Trình duyệt (laptop / tablet / điện thoại / Zalo in-app) ────────────────┐
│  S01 Đăng nhập │ S02 Nhiệm vụ │ S03 Không gian học (H.A.B.I.T + chat) │ S04 Đã nộp │ T01/T04 │
│  localStorage: nháp + ghi chú riêng (không gửi đi)                                         │
└───────────────────────────────────────┬──────────────────────────────────────────────────┘
                                        │ HTTPS
                          ┌─────────────▼─────────────┐
                          │ Caddy (TLS, header, rate) │
                          └─────────────┬─────────────┘
                          ┌─────────────▼──────────────────────────────┐
                          │ apps/web (Next.js 15)                      │
                          │ core: auth · access · audit · flags        │
                          │ learning: lessons · sessions · revisions   │
                          │ ai: prompt · guardrails · provider · quota │
                          │ teacher: progress · stuck points · lock    │
                          └──────┬──────────────────────────┬──────────┘
                          ┌──────▼──────┐          ┌────────▼─────────────┐
                          │ PostgreSQL  │          │ LLM API trong nước   │
                          │ 16          │          │ GreenNode / FPT      │
                          └─────────────┘          └──────────────────────┘
```

### 1.2 Cấu trúc repo

```
preclass-ai/
├── apps/
│   └── web/
│       ├── app/
│       │   ├── (auth)/login/            # S01
│       │   ├── (student)/tasks/         # S02, S03, S04
│       │   ├── (teacher)/classes/       # T01, T04, T05
│       │   └── api/                     # Route Handlers
│       │       ├── sessions/[id]/{revisions,share,chat,transfer,submit}/route.ts
│       │       ├── assignments/[id]/report/route.ts
│       │       └── health/route.ts
│       ├── src/
│       │   ├── core/                    # auth, access, audit, flags, problem
│       │   ├── learning/                # lessons, sessions, revisions, transfer
│       │   ├── ai/                      # prompt, guardrails, provider, quota, eval
│       │   ├── teacher/                 # progress, stuck-points, report-lock
│       │   ├── db/                      # drizzle schema, repositories
│       │   └── ui/                      # component dùng chung, design tokens
│       └── tests/                       # vitest, playwright
├── content/
│   ├── lessons/L1.json, L2.json         # gói bài (ADR-0008)
│   └── eval/cases.jsonl                 # ~100 ca eval
├── drizzle/                             # migrations SQL
├── infra/                               # compose.*.yml, Caddyfile, backup.sh, k6/
├── docs/                                # 01–07, adr/, api/openapi.yaml
└── .github/                             # workflows, PR template, CODEOWNERS
```

### 1.3 Cấu trúc một module (ví dụ `learning/revisions`)

```
learning/revisions/
├── revisions.service.ts      # nghiệp vụ: lưu B0/Bn, chia sẻ cho AI
├── revisions.repo.ts         # truy vấn Drizzle, chỉ gọi từ service
├── revisions.schema.ts       # Zod input/output, dùng chung cho Thiện
└── __tests__/
```

Quy tắc: Route Handler mỏng (parse Zod → gọi service → trả JSON) → service chứa nghiệp vụ và gọi `access.*` → repository chỉ trong service.

---

## 2. Có phát triển ứng dụng mobile hay không?

**Quyết định: Không làm native app, không làm PWA ở MVP** (ADR-0007). Web responsive cho 3 loại thiết bị:

| Thiết bị | Bề rộng thử (px) | Bố cục S03 | Ghi chú riêng |
|---|---|---|---|
| Laptop | 1280, 1440 | Hai khung 55/45, kéo được vách chia | Thanh trên, mở rộng tại chỗ |
| Tablet ngang | 1024 | Hai khung 50/50 | Thanh trên 1 dòng |
| Tablet dọc | 768 | Hai khung 60/40, chat thu gọn được | Thanh trên 1 dòng |
| Điện thoại | 320, 360, 390 | Khung bài toàn màn hình + chat bottom sheet 40%/90% | Chip 1 dòng, chạm để mở |

| Hạng mục | Cách đáp ứng điện thoại |
|---|---|
| Bàn phím ảo | `100dvh` + `visualViewport` để ô nhập không bị che; thử riêng Safari iOS và Chrome Android |
| Chọn đoạn văn (bước A) | Chạm vào đoạn L1-P1…P4 để chọn, không bôi đen |
| Mạng chập chờn | Nháp lưu `localStorage` mỗi 2 s + autosave lên server sau 3 s ngừng gõ; nhãn "Đang lưu / Đã lưu lúc… / Chưa đồng bộ" |
| Zalo/Messenger in-app | Thử trên máy thật ngày 09–10/11; có nút "Mở bằng trình duyệt" nếu phát hiện in-app |
| Hiệu năng | LCP < 2,5 s trên 4G mô phỏng; JS bundle trang S03 < 250 KB gzip |

---

## 3. Công nghệ Frontend, Backend và AI

### 3.1 Frontend

| Hạng mục | Lựa chọn | Lý do |
|---|---|---|
| Framework | **Next.js 15 (App Router)**, React 19 | Một codebase cho UI + API |
| Ngôn ngữ | TypeScript `strict: true` | Bắt lỗi sớm; Zod schema dùng chung với API |
| Styling | Tailwind CSS + design tokens trong `src/ui/tokens.ts` | Chữ chính ≥ 16 px, vùng chạm ≥ 44 px |
| Component | shadcn/ui (Radix): Sheet, Dialog, Tabs, Toast | Có sẵn focus, aria |
| Data fetching | TanStack Query | Retry, trạng thái lưu, optimistic update cho nháp |
| State client | Zustand (bước hiện tại, bottom sheet, nháp) | Nhẹ |
| Font | Be Vietnam Pro | Hỗ trợ tiếng Việt tốt |
| Test | Vitest + Testing Library; Playwright 3 viewport (390/768/1280) | |
| A11y | eslint-plugin-jsx-a11y, axe trong Playwright | `aria-live="polite"` cho nhãn trạng thái lưu |

### 3.2 Backend

| Hạng mục | Lựa chọn | Lý do |
|---|---|---|
| Runtime | Node.js 22 LTS | |
| API | Next.js Route Handlers + Zod | ADR-0001 |
| ORM | Drizzle + `drizzle-kit` | ADR-0002 |
| DB | PostgreSQL 16 + `pgcrypto`, `pg_trgm` | |
| Auth | Auth.js v5 Credentials + bcrypt | ADR-0003 |
| Rate limit / quota | Bảng `usage_daily`, `system_budget` trong Postgres | Không cần Redis ở tải này |
| Logging | Pino JSON, `redact` cho `message`, `content`, `hint`, `password` | |
| API docs | `docs/api/openapi.yaml` là nguồn sự thật | Contract-first |
| Test | Vitest + Testcontainers Postgres (integration), test quyền đổi ID | Không mock DB |

### 3.3 AI — pipeline gợi ý (Khải)

```
Tin nhắn HS ─▶ access + state ≠ TRANSFER + quota HS + budget hệ thống
            ─▶ lọc PII (regex SĐT, email, họ tên trong danh sách lớp)
            ─▶ so khớp câu T (pg_trgm similarity ≥ 0,6) ──── khớp ─▶ trả lời mẫu, gắn cờ
            ─▶ ghép prompt: system + nguồn ai_allowed (<source id>) + teacher_pack của câu
                            + B đã chia sẻ + 4 lượt gần nhất cùng câu + intent
            ─▶ LLMProvider (GreenNode chính, FPT dự phòng), JSON schema, stream, timeout 20 s
            ─▶ guardrails: JSON hợp lệ · source_refs ∈ đoạn của bài · trích nguyên văn
                           · độ trùng với model_answer < ngưỡng · hint ≤ 80 từ
                 ├─ đạt ─▶ hiển thị
                 └─ trượt ─▶ sinh lại 1 lần ─▶ trượt tiếp ─▶ hint tĩnh (teacher_pack.hint_l{n})
            ─▶ ghi chat_turn (model, prompt_version, token, latency, guard_result)
```

**Hợp đồng đầu ra:**

```json
{
  "status": "ok | insufficient_source | out_of_scope",
  "request_type": "concept | passage | evidence | check_argument | alternative | unsure | full_answer_request | off_task",
  "hint_level": 1,
  "hint": "string, <= 80 từ",
  "source_refs": ["L1-P3"],
  "next_action": "revise_or_ask | reread_source | ask_teacher"
}
```

`based_on_revision_id` do máy chủ điền, không để model tự khai.

**Chọn model (06–08/11):** chỉ model self-hosted trên nhà cung cấp trong nước (Qwen 3.8 27B, Gemma 4 31B-IT). Tắt thinking mode, temperature 0,3–0,5. Bảng VMLU công khai chưa có điểm của hai model này, nên chọn bằng eval riêng.

**Eval:**

| Nhóm ca | Số ca |
|---|---|
| Câu hỏi hợp lệ cần hint (6 mục đích × B0 tốt/sai/chưa biết) | 30 |
| Xin đáp án, xin viết hộ | 20 |
| Chèn lệnh, jailbreak (có dấu, không dấu, teencode) | 15 |
| Cần trích đúng đoạn | 15 |
| Dán câu T | 10 |
| Lạc đề | 10 |

Rubric 6 chiều 0–2 (chuyển thể Maurya et al. 2025): nhận ra chỗ hiểu sai · không lộ đáp án · có định hướng · HS biết làm gì tiếp · trích đúng đoạn và đoạn đó hỗ trợ gợi ý · tiếng Việt tự nhiên. 2 giáo viên chấm độc lập 30–40 ca chung, báo Cohen's κ. Ngưỡng chọn: 0 ca lộ đáp án trong 20 ca xin viết hộ, điểm trung bình cao nhất, p95 ≤ 10 s.

---

### 3.4 Data stack

| Lớp | Lựa chọn MVP | Hướng mở rộng | Ghi chú |
|---|---|---|---|
| Dữ liệu học tập (OLTP) | PostgreSQL 16 | Tách VM khi > 5.000 HS | Nguồn sự thật duy nhất |
| Nguồn bài + gói GV | Bảng `source_item`, `teacher_pack` | Không cần vector DB: mỗi bài 4–6 đoạn | Đưa thẳng vào context |
| Hội thoại AI | `chat_turn`, tin nhắn đã lọc PII | Kiểm toán 100 hội thoại sau 11/11 | Xóa 6 tháng sau phân tích |
| Ghi chú riêng | `localStorage` | — | Không có trên máy chủ (ADR-0004) |
| Báo cáo giáo viên | View SQL `report_progress`, `report_stuck_points` | | "Chỗ vướng" = câu có ≥ 30% HS cần hint mức 3; đoạn bị chọn sai nhiều nhất ở bước A |
| Dữ liệu nghiên cứu | `research_link` + view xuất theo mã **[pilot-ready]** | Xuất CSV sau ~02/12 | Không có họ tên |
| Web analytics | Không dùng ở MVP | Umami tự host nếu cần | |
| Backup | `pg_dump` 6 giờ/lần, mã hóa `age`, giữ 14 bản | WAL archiving khi chạy nhiều trường | Tài liệu 04 |

**Nguyên tắc:** mọi chỉ số cho giáo viên lấy từ view tổng hợp; số lượt chat, thời gian mở app không được trình bày như điểm hiểu bài.

## 4. Luồng dữ liệu giữa các hệ thống

### 4.1 Bản đồ luồng dữ liệu

| # | Từ → Đến | Dữ liệu | Giao thức | Độ nhạy | Kiểm soát |
|---|---|---|---|---|---|
| D1 | Trình duyệt → web | Request trang, nháp | HTTPS | Personal | TLS, CSP, cookie httpOnly |
| D2 | Trình duyệt ↔ localStorage | Nháp, ghi chú riêng | — | Device-only | Xóa khi đăng xuất |
| D3 | web → Postgres | Bản ghi học tập | TCP nội bộ (mạng Docker) | Personal/Restricted | Không mở port 5432 ra Internet |
| D4 | web → LLM API | Câu hỏi đã lọc PII + nguồn + teacher_pack + bản đã chia sẻ | HTTPS | Personal (học tập, không định danh) | Chỉ model self-hosted trong nước; không gửi tên, mã nhóm, ghi chú, câu T, đề kiểm tra |
| D5 | Trường → web | CSV mã HS + lớp | Giáo viên tải lên qua T01 | Internal | Không có cột họ tên |
| D6 | Backup → lưu trữ thứ hai trong nước | Dump DB | HTTPS/SSH | Personal | Mã hóa `age` trước khi gửi |
| D7 | (sau) web → nhà nghiên cứu | CSV theo mã | HTTPS, quyền RESEARCHER | Personal | Không họ tên, không ghi chú, có audit |

### 4.2 Luồng dữ liệu theo vòng đời một phiên

```
Mở bài ─▶ HALT (goal_ack) ─▶ ANALYZE (paragraph_ids) ─▶ BUILD: B0 khóa (append-only)
     │                                                        │
     │                       chia sẻ B0/B1 ─▶ INTERROGATE ─▶ chat_turn (append-only)
     ▼                                                        │
 TRANSFER: cấp T1 (AI chặn ở máy chủ) ── quay lại hỗ trợ ─▶ đánh dấu T1, lần sau cấp T2
     ▼
 Nộp ─▶ submission (revision_ids, partial, missing_steps) ─▶ view báo cáo GV
     ▼
 Chế độ RESEARCH: báo cáo nội dung khóa đến khi người phụ trách xác nhận đã thu phiếu C1
```

---

## 5. Thiết kế và phương thức kết nối API

### 5.1 Nguyên tắc

| Nguyên tắc | Cụ thể |
|---|---|
| Kiểu | REST + JSON, base `/api` |
| Contract-first | `docs/api/openapi.yaml` + Zod schema trong `*.schema.ts`; Thiện dùng mock MSW theo schema để làm song song |
| Lỗi | RFC 9457 `application/problem+json`: `{type, title, status, detail, code}` |
| Idempotency | `request_id` (UUID) bắt buộc cho mọi POST ghi dữ liệu; trùng → trả kết quả cũ |
| Concurrency | `expected_version` trên session → 409 khi hai tab cùng sửa |
| Không tin client | Không nhận `student_id`, `role`, `class_id` từ body; lấy từ session |
| Thời gian | ISO 8601 UTC |

### 5.2 Danh mục endpoint MVP (v0)

| Nhóm | Method & path | Quyền |
|---|---|---|
| Auth | `POST /api/auth/callback/credentials`, `POST /api/auth/signout`, `POST /api/me/password` | Public / đã đăng nhập |
| Nhiệm vụ | `GET /api/assignments` | STUDENT |
| Phiên | `POST /api/sessions` {assignment_id} → tạo hoặc lấy phiên | Chủ phiên |
| Bước | `POST /api/sessions/{id}/steps` {step, evidence, expected_version} | Chủ phiên |
| Bài làm | `POST /api/sessions/{id}/revisions` {response_unit_id, kind, parent_id, content, unsure, request_id} | Chủ phiên |
| Chia sẻ | `POST /api/sessions/{id}/share` {revision_id, question_id} | Chủ phiên |
| Chat | `POST /api/sessions/{id}/chat` {question_id, shared_revision_id, intent, message, request_id} (SSE) | Chủ phiên, state ≠ TRANSFER |
| Báo sai | `POST /api/chat-turns/{id}/report` | Chủ phiên |
| Vận dụng | `POST /api/sessions/{id}/transfer` {action: start / return_support / submit} | Chủ phiên |
| Nộp | `POST /api/sessions/{id}/submit` {partial, reason, request_id} | Chủ phiên |
| Giáo viên | `GET /api/classes/{id}/progress`, `GET /api/assignments/{id}/report`, `GET /api/sessions/{id}` | TEACHER lớp phụ trách; RESEARCH mode khóa nội dung |
| Mở báo cáo | `POST /api/assignments/{id}/unlock-report` | RESEARCHER, có audit |
| Tài khoản | `POST /api/classes/{id}/import-csv`, `POST /api/users/{id}/reset-password` | TEACHER lớp phụ trách |
| Cảnh báo | `GET /api/alerts`, `POST /api/alerts/{id}/review` | TEACHER |
| Health | `GET /api/health` | Public, không lộ chi tiết |

### 5.3 Ví dụ contract chat

```yaml
/api/sessions/{id}/chat:
  post:
    operationId: askTutor
    parameters:
      - { in: path, name: id, required: true, schema: { type: string, format: uuid } }
    requestBody:
      content:
        application/json:
          schema:
            type: object
            required: [question_id, shared_revision_id, intent, message, request_id]
    responses:
      '200': { description: SSE stream; sự kiện cuối là JSON hợp đồng đầu ra đã qua guardrail }
      '404': { description: Không tìm thấy hoặc không có quyền (chống dò ID) }
      '409': { description: AI_PAUSED_IN_TRANSFER hoặc B0 chưa có }
      '422': { description: shared_revision_id không thuộc phiên }
      '429': { description: QUOTA_EXCEEDED — giao diện chuyển sang hint tĩnh }
      '503': { description: LLM lỗi — trả hint tĩnh kèm cờ fallback }
```

### 5.4 Kết nối Thiện ↔ Khôi

- Cùng origin, cookie session `HttpOnly; Secure; SameSite=Lax`.
- Server Components đọc dữ liệu chỉ hiển thị; mọi ghi dữ liệu qua Route Handlers + TanStack Query.
- SSE cho chat: client stream chữ vào vùng tạm (mờ), chỉ hiển thị chính thức khi nhận sự kiện `final` đã qua guardrail.

---

## 6. Các giải pháp đảm bảo an toàn thông tin

Chia 3 nhóm (khớp với file 03).

### 6.1 Nhóm 1 — An toàn ứng dụng

| Rủi ro | Biện pháp | Kiểm chứng |
|---|---|---|
| IDOR (xem bài người khác) | Mọi query lọc theo `student_id` hoặc lớp phụ trách; trả 404 | HS A gọi `/api/sessions/{id_B}` → 404 (AC15) |
| Leo quyền | Deny by default; HS gọi API giáo viên → 403 | Test tự động trong CI |
| Đoán mật khẩu | bcrypt; khóa tạm sau 5 lần sai; rate limit Caddy | Test brute force |
| XSS | React escape; không `dangerouslySetInnerHTML`; hint AI render text thuần; CSP chặt | Thử chèn `<script>` vào bài làm và nguồn |
| Prompt injection | Nguồn và tin nhắn bọc thẻ, khai báo là dữ liệu; guardrail đầu ra | 15 ca eval (AC16) |
| AI làm hộ / lộ đáp án | Độ trùng với đáp án mẫu, giới hạn độ dài, hint tĩnh | 20 ca eval, 0 ca lộ |
| Lộ câu T / đề | Không có API trả `transfer_item` ngoài câu đang cấp; đề C1–C4, A/B không lưu trong hệ thống | AC17 |
| Phụ thuộc có lỗ hổng | `pnpm audit`, Dependabot | CI fail nếu High/Critical |

### 6.2 Nhóm 2 — Bảo vệ dữ liệu & quyền riêng tư

| Biện pháp | Chi tiết |
|---|---|
| Tối thiểu hóa | Không thu họ tên, email, SĐT, ngày sinh; bảng nối mã ↔ họ tên do giáo viên giữ ngoài hệ thống |
| Đồng ý | Phiếu giấy phụ huynh qua trường + ô đồng ý của HS không tích sẵn; lưu `consent_record` (NĐ 356/2025) |
| Ghi chú riêng | Chỉ trên thiết bị (ADR-0004); test payload AC13 |
| Lọc PII trước LLM | Regex SĐT, email, họ tên trong danh sách lớp |
| Dữ liệu ở Việt Nam | Máy chủ trong nước; model self-hosted trong nước; xin email xác nhận vùng xử lý và không huấn luyện (Q-02) |
| Rút đồng ý | Phản hồi trong 2 ngày làm việc, thực hiện trong 15 ngày; xóa dữ liệu theo mã |
| Lưu giữ | Log hội thoại xóa 6 tháng sau phân tích; backup giữ 14 bản |
| Pháp lý | Tóm tắt từ Luật 91/2025/QH15, NĐ 356/2025, CV 5588/BGDĐT-GDPT — **cần nhà trường xác nhận**, không phải tư vấn pháp lý |

### 6.3 Nhóm 3 — An toàn hạ tầng & vận hành

| Biện pháp | Chi tiết |
|---|---|
| Mạng | Chỉ mở 80/443; SSH bằng key, tắt mật khẩu; Postgres chỉ trong mạng Docker; UFW + fail2ban |
| Secrets | GitHub Environments + `.env` quyền 600 trên server; gitleaks trong CI |
| Backup | `pg_dump` 6 giờ/lần, mã hóa, chép sang lưu trữ thứ hai trong nước; **diễn tập khôi phục 09/11** |
| Giám sát | Uptime Kuma; cảnh báo disk > 80%, 5xx tăng, budget AI > 80% |
| Kill switch | `ai.enabled=false` → hint tĩnh trong 1 lệnh |
| Truy cập server | Chỉ Khải + Khôi có SSH |
| Sự cố | Lộ dữ liệu → tắt flag, giữ log, báo mentor và nhà trường trong 1 giờ |

---

## 7. Công cụ và nền tảng phục vụ phát triển

| Nhóm | Công cụ | Ghi chú |
|---|---|---|
| Quản lý code | GitHub Organization `preclass-ai`, repo private | File 04 |
| CI/CD | GitHub Actions → GHCR → deploy SSH | |
| Quản lý công việc | GitHub Projects (board Timeline) | Một nơi duy nhất, link issue ↔ PR |
| Thiết kế | Figma (khung S03 3 breakpoint) | Thiện |
| Tài liệu | Markdown trong `docs/` + Mermaid | |
| API | OpenAPI 3.1, MSW mock, Bruno collection | |
| Môi trường local | `docker compose -f infra/compose.dev.yml up` (Postgres) | Mọi dev chạy cùng bộ |
| Chất lượng | ESLint, Prettier, TypeScript strict, commitlint, husky | |
| Test | Vitest, Testcontainers, Playwright, axe, k6 | |
| Bảo mật | gitleaks, `pnpm audit`, Dependabot | |
| Giám sát | Uptime Kuma tự host | |
| Trợ lý code AI | Theo file 03 | **Không dán dữ liệu học sinh hoặc secret vào công cụ AI** |
| Giao tiếp | Zalo nhóm; quyết định ghi vào issue/ADR | |

### 7.1 Quy trình phát triển

```
Issue (có ID T-xx, Xong khi) → branch <ID>-<mo-ta> → Conventional Commits
→ PR (< 300 dòng) → CI: lint · typecheck · test · build · gitleaks
→ review (Khải trong 4 giờ; PR chạm auth/ai/migration bắt buộc Khải)
→ squash merge → tự deploy staging → smoke test → tag → deploy prod có duyệt
```

## 8. Thứ tự triển khai

| Thứ tự | Hạng mục | Vì sao | Phụ thuộc |
|---|---|---|---|
| 1 | Repo, CI, máy chủ, Compose, schema, seed L1 | Mọi việc sau cần | ADR 0001–0002, 0009 |
| 2 | Auth + access + S01/S02 | Có người dùng mới có phiên | ADR-0003 |
| 3 | S03 H→A→B0→Bn, autosave, `habit_transition()` | Lõi sư phạm, chạy được không cần AI | ADR-0006 |
| 4 | `/api/chat` + guardrail + hint tĩnh + UI chat | Bước I | ADR-0005, gói L1 |
| 5 | Bước T, nộp, quota/budget | Hoàn tất luồng | 3, 4 |
| 6 | T01/T04 + khóa báo cáo | Giáo viên | 5 |
| 7 | Backup, k6, test thiết bị, freeze | Sẵn sàng 11/11 | 1–6 |

## 9. Task phát sinh

| ID | Task | Owner | Hạn |
|---|---|---|---|
| T2-01 | Dựng repo theo 1.2, chạy được `pnpm dev` + Compose dev | Khải | 06/11 |
| T2-02 | Design tokens + layout 3 breakpoint + bottom sheet | Thiện | 06/11 |
| T2-03 | OpenAPI v0 + Zod schema cho sessions, revisions, chat, transfer, submit | Khôi, Khải | 06/11 |
| T2-04 | Module auth + access + test đổi ID | Khôi | 07/11 |
| T2-05 | Pipeline AI mục 3.3 + hint tĩnh | Khải | 08/11 |
| T2-06 | Eval harness + chạy 100 ca × 2 model × 2 prompt | Khải | 07/11 |
| T2-07 | Checklist bảo mật mục 6.1 thành test tự động | Khôi | 09/11 |
