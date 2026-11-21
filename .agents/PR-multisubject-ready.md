# PR D4: chuẩn bị đa môn tối thiểu và tài liệu (feat/multisubject-ready)

Xếp chồng trên D3. Migration 0010 chỉ thêm bảng `subject` (đánh số lại sau 0008 plan_job và 0009 remediation).

- Bảng `subject` (danh mục môn GDPT, chỉ Địa lí hoạt động); parser giáo án đã được kiểm với giáo án mô phỏng Lịch sử (test D1).
- `docs/security/PHAP-LY-DU-LIEU.md`: bảng đã kiểm chứng và cần đối chiếu: NĐ 356/2025 (hiệu lực 01/01/2026, thay NĐ 13/2023: đã đọc), Luật 91/2025/QH15 (chưa đọc được nội dung, trang 403), CV 5588 (là công văn 19/08/2026 hướng dẫn triển khai, khung ban hành bằng QĐ 2422/QĐ-BGDĐT). ADR-0013 đã bỏ viện dẫn NĐ 13/2023.
- `docs/Proposal.md` mục 8: chỉ LearnLM/Eedi 2025 đọc được và có số liệu (n=165, 76,4%, 66,2% so với 60,7%, chưa bình duyệt); 5 nguồn còn lại không đọc được nên không ghi số (đường dẫn Låg và Sæle trả về bài khác); lộ trình đa môn, kế hoạch sau thi.
- Trang `/du-lieu` "Dữ liệu của em đi đâu" (link ở đăng nhập, /thu, khu vực học sinh); `GET /v1/auth/config` thêm `chatMode`, `aiProvider` (chỉ tên máy chủ).
- RUNBOOK: Groq Free và chiến lược tiết kiệm token, `DEMO_REPLAY`.

Chưa làm: cột `subject` trên `lesson` (P2); tự động xóa dữ liệu sau 90 ngày (hiện chạy tay `purge_guests.py`).
