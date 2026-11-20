# PR: Nạp giáo án nhiều định dạng DOCX, PDF, XLSX, PPTX (feat/lesson-plan-upload)

Base: `main`. Threat model: `docs/security/THREAT-MODEL-upload.md`. Pipeline sinh nội dung **không đổi** (vẫn dùng anchors, MockProvider mặc định).

## Làm gì
- `POST /v1/sources/file` (multipart): loại tệp theo magic bytes + `[Content_Types].xml`, bỏ qua tên và Content-Type. `/sources/docx` cũ giữ nguyên.
- Cổng tệp độc (zip bomb, macro, nhúng/ngoài, đường dẫn lạ, PDF có JavaScript/đính kèm/mật khẩu, Office cũ, giả đuôi) trước khi mở bằng thư viện; parse trong **tiến trình con** (timeout 30 s, `RLIMIT_AS` trên Linux, một parse mỗi lúc).
- Parser: PDF (`pypdf`, anchor `{page, para}`), XLSX (`openpyxl` read-only + data-only, chỉ giá trị lưu, `{sheet,row,col,header?}`, số chuẩn hóa dạng "23,2"), PPTX (`python-pptx`, `{slide,shape,para}` / `{slide,shape,row,col}`). PDF scan → 201 + `extractStatus=FAILED`, `extractError=SCANNED_PDF`, không OCR. Nguồn FAILED không dùng để tạo/đổi nguồn của bài (422 `SOURCE_NOT_READABLE`).
- S01: vùng kéo-thả 4 định dạng, kết quả (số anchor, cảnh báo), xem trước anchors theo trang/sheet/slide, locator thân thiện ("Trang 3, đoạn 2", "Sheet Dân số, ô C5", "Slide 4"), lỗi tiếng Việt.
- Thêm phụ thuộc: `pypdf`, `openpyxl`, `python-pptx`, `defusedxml` (đều thuần Python, kéo thêm `pillow`, `xlsxwriter` qua python-pptx).

## Fixture độc đã chặn (đều có test)
| Fixture | Kết quả |
|---|---|
| zip bomb .docx/.xlsx/.pptx (30 MB giải nén từ ~30 KB) | 422 `FILE_TOO_LARGE` |
| 1001 entry | 422 `INVALID_FILE` |
| macro (`vbaProject.bin`, content-type macroEnabled) docx/xlsx/pptx | 422 `MACRO_REJECTED` |
| externalLinks (xlsx), embeddings (pptx) | 422 `EXTERNAL_CONTENT_REJECTED` |
| PDF `/OpenAction` JavaScript, `/EmbeddedFiles` | 422 `ACTIVE_CONTENT_REJECTED` |
| PDF mật khẩu | 422 `INVALID_FILE` |
| PDF 51 trang | 422 `SOURCE_TOO_LARGE` |
| PDF > 10 MB | 422 `FILE_TOO_LARGE` |
| PNG/EXE/OLE (.xls cũ) đặt đuôi .pdf/.docx/.xlsx | 422 `INVALID_FILE` |
| entry `../evil` | 422 `INVALID_FILE` |
| Excel công thức (`=SUM`, `=cmd|...`) | không có anchor chứa `=`, không tính |
| PDF scan | 201, FAILED, `SCANNED_PDF` |
| parser treo (timeout 0) | 422 `PARSE_TIMEOUT`, tiến trình con bị kill |
| GV khác xem nguồn PRIVATE | 404 |

## Kiểm tra
pytest 246 passed, 1 skipped (+24 test tích hợp, +17 unit); ruff, mypy --strict sạch; OpenAPI + api-client sinh lại. Web lint/typecheck sạch, vitest 45 passed. Playwright upload.spec 390/768/1280/WebKit 8/8; teacher/sources-refresh/auth 15/15. Ảnh: `apps/web/test-results/upload/*.png` (gitignored).

## Env mới (Render)
`SOURCE_MAX_PDF_PAGES=50`, `SOURCE_MAX_XLSX_SHEETS=5`, `SOURCE_MAX_XLSX_CELLS=2000`, `SOURCE_MAX_PPTX_SLIDES=60`, `SOURCE_PARSE_TIMEOUT_S=30`, `SOURCE_PARSE_MEM_MB=600`: đều đã có mặc định, không bắt buộc đặt.

## Rủi ro / chưa làm
Không quét mã độc, không OCR. `RLIMIT_AS` chỉ có trên Linux và **chưa thử trên Render**: nếu tệp hợp lệ bị `INVALID_FILE` hàng loạt, chỉnh `SOURCE_PARSE_MEM_MB`. Spawn tiến trình con tốn ~0,5–1 s mỗi tệp. Pipeline sinh ghép ô theo (row, col) không theo sheet nên XLSX nhiều sheet có thể trộn ô (khuyến nghị 1 sheet dữ liệu). Chưa có endpoint "bản mới từ tệp" cho định dạng ngoài DOCX (`/revisions/docx` giữ nguyên). docs/Proposal.md chưa có trên nhánh này nên chưa cập nhật mục Giải pháp.
