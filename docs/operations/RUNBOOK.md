# RUNBOOK — staging/prod (GĐ10)

Stack: `postgres` + `api` (FastAPI) + `web` (Next.js) + `caddy` (TLS, `/v1/*` → api, còn lại → web) + `backup` (tùy chọn). Chi tiết bổ sung: `deployment-runbook.md`, `backup-restore-runbook.md`, `monitoring-runbook.md`.

## Chạy staging trên máy sạch

```bash
cd infra
cp .env.staging.example .env.staging     # đổi POSTGRES_PASSWORD (và trong DATABASE_URL), SESSION_SECRET, SEED_PASSWORD, APP_HOSTNAME, FRONTEND_ORIGIN
docker compose -f compose.staging.yml up -d --build   # build api+web tại chỗ; api tự migrate, SEED_DEMO=true thì seed
python ../scripts/smoke.py --base https://localhost --insecure --password "<SEED_PASSWORD>"   # in "SMOKE OK"
```

- `FRONTEND_ORIGIN` phải bằng `https://$APP_HOSTNAME` (kiểm tra Origin chống CSRF của API); sai → mọi POST trả 403 `CSRF`.
- `APP_HOSTNAME=localhost` → Caddy dùng CA nội bộ (trình duyệt cảnh báo; smoke dùng `--insecure`). Tên miền thật → Let's Encrypt, cần cổng 80/443 mở.
- Chỉ staging có seed (`SEED_DEMO=true`, `APP_ENV=staging`). **Prod: `APP_ENV=production`, `SEED_DEMO=false`**; seed từ chối chạy khi `APP_ENV=production`. Tài khoản seed: `gv.dia@preclass.local`, `HS10-01..15`, `HS11-01..15`, `admin@preclass.local`.
- Prod dùng image từ registry: `IMAGE_TAG=<sha> docker compose -f compose.prod.yml pull && ... up -d` (bỏ `--build`).
- `smoke.py` ghi dữ liệu thật (nguồn, bài, bài giao) → **chỉ chạy trên staging**.

## Backup / restore

- Bật: tạo `infra/backup-recipients.txt` (khóa công khai `age`, giữ khóa bí mật ngoài server), rồi `docker compose -f compose.staging.yml --profile backup up -d backup`. Mỗi 24 giờ: `pg_dump | gzip | age` vào volume `backups-<env>`, xóa file > 14 ngày.
- Restore: `infra/restore.sh` (xem `backup-restore-runbook.md`). **Diễn tập restore trên staging trước khi dùng prod.**
- Backup chưa bật = chưa có bản sao nào của dữ liệu học sinh.

## Sự cố thường gặp

| Triệu chứng | Xử lý |
|---|---|
| `api` unhealthy | `docker compose logs api`: lỗi migrate (DB chưa sẵn sàng/mật khẩu lệch giữa `POSTGRES_PASSWORD` và `DATABASE_URL`) |
| Đăng nhập OK nhưng thao tác 403 `CSRF` | `FRONTEND_ORIGIN` ≠ origin trình duyệt |
| Cookie không giữ trên http | `COOKIE_SECURE=true` cần https; chỉ đặt `false` cho dev |
| Generate trả 503 `AI_DISABLED` | `AI_ENABLED=false`; phần còn lại vẫn chạy |
| Job generate kẹt | restart `api`: job RUNNING chuyển FAILED, tạo lại |
| Giới hạn đăng nhập sai (rate limit) lệch/mất | chạy API với `--workers 1`: bộ đếm nằm trong bộ nhớ từng tiến trình; không tăng worker khi chưa chuyển sang kho dùng chung |
| Chạy `up` lỗi cổng 80/443 | cổng bị chiếm; dừng dịch vụ đang dùng |

## Rollback

`IMAGE_TAG=<tag cũ> docker compose -f compose.prod.yml up -d`. Migration chỉ tiến (`alembic upgrade head` lúc khởi động); lùi schema cần `alembic downgrade` thủ công **sau khi backup**.

## Demo preview trên laptop (19/11)
- Khởi động: bật Docker Desktop → `PYTHONPATH=. uv run python -m alembic upgrade head && uv run python -m seed.seed` (trong `apps/api`, nếu DB trống) → `cd apps/web && corepack pnpm@10 build` (EPERM ở bước standalone là chấp nhận được) → `powershell -File scripts\ops\preview.ps1`. URL mới ở `.agents/PREVIEW_URL.md`, basic auth ở `apps/api/data/preview-credentials.txt`. Tắt: `scripts\ops\preview-stop.ps1`.
- Khởi động lại sau khi tunnel chết: `preview-stop.ps1` rồi `preview.ps1` (URL đổi). Không build lại web nếu mã không đổi.
- Quay lui: `git checkout pre-merge-2026-11-19` (hoặc revert merge PR #8), build lại web, khởi động lại preview.
- Khôi phục DB từ backup: `docker exec -i infra-postgres-1 psql -U preclass -d preclass -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"` rồi `docker exec -i infra-postgres-1 psql -U preclass -d preclass < apps/api/data/backup/predeploy-1911.sql`. Thử khôi phục vào DB tạm `preclass_restore_check` trước. Chỉ đụng database `preclass`, không xoá volume.
- Reset về seed sạch: `DROP SCHEMA public CASCADE; CREATE SCHEMA public;` trên `preclass`, rồi migrate + seed như trên.

## Giới hạn nạp tệp (DOCX, PDF, XLSX, PPTX)

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `SOURCE_MAX_PDF_PAGES` | 50 | Số trang PDF tối đa |
| `SOURCE_MAX_XLSX_SHEETS` / `SOURCE_MAX_XLSX_CELLS` | 5 / 2000 | Số sheet; số ô có dữ liệu mỗi sheet |
| `SOURCE_MAX_PPTX_SLIDES` | 60 | Số slide |
| `SOURCE_PARSE_TIMEOUT_S` | 30 | Quá hạn thì tiến trình con bị kill (422 `PARSE_TIMEOUT`) |
| `SOURCE_PARSE_MEM_MB` | 600 | `RLIMIT_AS` của tiến trình con (chỉ Linux). Hạ xuống nếu Render báo thiếu RAM; tăng nếu tệp hợp lệ bị `INVALID_FILE` do hết bộ nhớ. 0 = không giới hạn |

Cứng trong code: 10 MB mỗi tệp, ≤ 1000 entry, ≤ 20 MB giải nén. Mỗi lúc chỉ chạy một parse. Không có quét mã độc và không OCR: PDF scan được lưu ở trạng thái FAILED (`SCANNED_PDF`). Triệu chứng và cách xử: nhiều `PARSE_TIMEOUT` → tệp quá nặng, yêu cầu GV xuất lại; `INVALID_FILE` hàng loạt sau khi deploy → kiểm tra `SOURCE_PARSE_MEM_MB`.

## Habit (chat và thói quen học)

| Biến môi trường | Mặc định | Ý nghĩa |
|---|---|---|
| `CHAT_ENABLED` | `false` | Bật Habit. Tắt: route 404, UI ẩn, hệ thống như cũ. Đổi cần restart API. |
| `CHAT_MODE` | `rule` | `rule` = 0đ, không gọi LLM. `llm` = rule vẫn quyết định và hậu kiểm, LLM chỉ viết lại. |
| `CHAT_LLM_BASE_URL`, `CHAT_LLM_API_KEY`, `CHAT_LLM_MODEL` | rỗng | Chỉ khi `llm`. Thiếu một biến thì tự dùng rule. Khóa đặt trên Render, không commit. |
| `CHAT_MAX_OUTPUT_TOKENS` / `CHAT_DAILY_TOKEN_BUDGET` | 220 / 300000 | Hết ngân sách ngày thì tự dùng rule (học sinh không thấy lỗi). |
| `CHAT_MAX_PER_DAY_PER_STUDENT` / `CHAT_MAX_PER_ITEM` | 30 / 6 | Quá hạn mức → 429 thân thiện. |
| `HABIT_DAILY_GOAL` | 3 | Mục tiêu câu/ngày. |

Giá trị đề xuất trên Render cho đợt thử: `CHAT_ENABLED=true`, `CHAT_MODE=rule`, còn lại mặc định. Tắt khẩn cấp: `CHAT_ENABLED=false` rồi restart. Cần migration `alembic upgrade head` (0003) trước khi bật.

Xem tokens và số lần bị chặn: đăng nhập ADMIN rồi `GET /v1/admin/survey/stats` (`chatTotal, chatFallbackRate, chatBlocked, chatTokensIn/Out`). Red team trước khi bật `llm`: `cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/habit_redteam.py` (0 vi phạm). Giữ uvicorn `--workers 1`: cache và giới hạn dùng bộ nhớ một tiến trình.

## Cá nhân hóa (lựa chọn của học sinh, chế độ tập trung)

`PERSONALIZATION_ENABLED` (mặc định `false`): bật thì học sinh thấy "Em muốn học theo cách nào hôm nay?" và nút "Chế độ tập trung" ở bài; tắt thì route trả 404 và UI ẩn. Đổi cần restart API; cần `alembic upgrade head` (0004) trước khi bật. Habit (`CHAT_ENABLED=true`) không bắt buộc, nhưng lời khuyên theo kỹ năng và cách gợi ý ngắn/ưu tiên bảng chỉ có khi Habit bật. Giá trị đề xuất cho đợt thử: `CHAT_ENABLED=true`, `PERSONALIZATION_ENABLED=true`. Xóa dữ liệu của một học sinh: `DELETE FROM student_preference WHERE student_id = ...`.

## Quy trình merge

1. Chỉ merge khi **CI xanh** và PR có **báo cáo test** (lệnh đã chạy và kết quả: ruff, mypy --strict, pytest, OpenAPI khớp code, web lint/typecheck/vitest/build; Playwright theo viewport khi đổi giao diện).
2. **Không resolve conflict trên GitHub web.** Có conflict thì gộp `main` vào nhánh ở máy, giải conflict, chạy lại đúng các bước CI rồi push. Lý do: bản giải trên web đã làm mất nội dung (biến `source_*`, CSS upload, mục tài liệu) mà không báo lỗi.
3. **Merge từng nhánh một**, theo thứ tự phụ thuộc. Trước khi merge nhánh kế tiếp, gộp `main` mới nhất (đã có nhánh vừa merge) vào nhánh đó, giải conflict ở máy và chạy lại CI.
4. Sau merge: kiểm tra Render chạy đúng commit; không xóa nhánh cho đến khi xong bước này.
5. Số liệu cứng trong test (`test_contract` đếm operation, tiêu đề CSV) phải khớp openapi thật: đếm từ `openapi.json`, không tính nhẩm.

## Seed và dữ liệu khảo sát

`python -m seed.seed` **bỏ qua** khi DB đã có dữ liệu, nên sửa nội dung seed (ví dụ chống lộ đáp án) chỉ có hiệu lực trên DB mới. Reset DB demo xóa bài làm của học sinh: xuất `GET /v1/admin/survey/export.csv` trước, và không reset giữa chừng một đợt khảo sát. Kiểm tra seed không lộ đáp án: `cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/check_seed_leak.py` (0 vi phạm; CI chạy cùng kiểm tra trong `tests/unit/test_seed_leak.py`).

## HABIT AI với model thật (CHAT_MODE=llm)

Mặc định `CHAT_MODE=rule` (0đ, không gọi model). Bật model thật chỉ khi cần phần diễn đạt tự nhiên hơn và phần "gợi ý thêm". Luật vẫn quyết định trước (không đáp án, không phản hồi gợi đáp án, lọc PII) và kiểm lại sau mỗi câu trả lời của model; lỗi, hết ngân sách hoặc quá 15 giây thì dùng câu trả lời của luật, học sinh không thấy lỗi.

| Biến | Giá trị |
|---|---|
| `CHAT_MODE` | `llm` |
| `CHAT_LLM_BASE_URL`, `CHAT_LLM_API_KEY`, `CHAT_LLM_MODEL` | xem hai lựa chọn dưới đây; khóa chỉ đặt trong biến môi trường của Render, không commit, không dán vào chat |
| `CHAT_AI_EXTRA` | `true` để thêm phần thứ hai "HABIT AI gợi ý thêm (chưa được thầy cô kiểm chứng)" (kiến thức chung). Mặc định `false`. Chỉ có tác dụng khi `CHAT_MODE=llm` |
| `CHAT_DAILY_TOKEN_BUDGET` | giữ `300000` (hết thì tự về luật); `CHAT_MAX_OUTPUT_TOKENS=220` |

Hai lựa chọn giá rẻ (đều theo chuẩn OpenAI `chat/completions`, đã có sẵn `OpenAICompatibleProvider`):
1. **DeepSeek**: `CHAT_LLM_BASE_URL=https://api.deepseek.com`, `CHAT_LLM_MODEL=deepseek-chat`.
2. **Qwen bản quốc tế (DashScope, máy chủ Singapore)**: `CHAT_LLM_BASE_URL=https://dashscope-intl.aliyuncs.com/compatible-mode/v1`, `CHAT_LLM_MODEL=qwen-plus` (hoặc model rẻ hơn cùng họ). Khóa theo vùng: khóa Singapore khác khóa Bắc Kinh. Nguồn: tài liệu "OpenAI compatibility" của Alibaba Cloud Model Studio. Kiểm lại tên model và giá trên trang nhà cung cấp trước khi bật.

**Dữ liệu gửi ra ngoài:** nội dung câu hỏi của học sinh (đã lọc số điện thoại, email, địa chỉ; không có tên, mã khảo sát hay tài khoản), đề bài, các phương án (không đánh dấu đúng) và đoạn nội dung bài đã duyệt (tối đa 1.200 ký tự). **Không bao giờ** gửi đáp án hoặc lời giải của câu chưa nộp. Nếu ưu tiên dữ liệu, chọn Qwen quốc tế (máy chủ Singapore) và nói rõ với nhà trường trước khi bật. Cả hai nhà cung cấp là bên thứ ba ngoài nước.

Kiểm tra trước khi bật (cần khóa trong môi trường, không lưu khóa): `cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/llm_smoke.py --extra`. Script chạy 10 câu mẫu và 10 câu tấn công qua model thật cùng bộ lọc của API, in kết quả; thoát 0 khi không có vi phạm. Chỉ bật khi 0 vi phạm. Xem tokens và số lần bị chặn: `GET /v1/admin/survey/stats` (`chatBlocked`: `LLM_ANSWER`, `LLM_NUMBER`, `LLM_PII`, `LLM_PROMPT`, `LLM_ERROR`, `LLM_BUDGET`; phần thứ hai bị bỏ không ghi lý do riêng).
