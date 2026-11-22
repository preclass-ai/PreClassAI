"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api, unwrap } from "@/lib/api";

/** "Dữ liệu của em đi đâu": public, short, written for students. Places and retention wording must match what really happens (see docs/security/PHAP-LY-DU-LIEU.md). */
export default function DataPage() {
  const cfg = useQuery({ queryKey: ["auth-config"], queryFn: () => unwrap(api.GET("/v1/auth/config")), staleTime: 300_000 });
  const llm = cfg.data?.chatMode === "llm" && cfg.data.aiProvider;
  return (
    <main className="login-page">
      <div className="card login-card stack" style={{ maxWidth: 720 }}>
        <p className="login-brand">
          ◉ <span>PreClass AI</span>
        </p>
        <h1>Dữ liệu của em đi đâu</h1>
        <section aria-labelledby="d-thu">
          <h2 id="d-thu">Mình thu gì</h2>
          <ul>
            <li>Mã khảo sát của em (dạng KS-XXXX). Mã này không phải tên em.</li>
            <li>Câu em chọn, đúng hay sai ở lần đầu, và lúc em nộp.</li>
            <li>Em đã xin gợi ý mấy lần.</li>
            <li>Câu em hỏi HABIT AI. Số điện thoại, email và địa chỉ được lọc bỏ trước khi lưu.</li>
          </ul>
          <p>Mình không thu tên, lớp, email hay số điện thoại. Em cũng đừng gõ những thông tin đó vào ô hỏi nhé.</p>
        </section>
        <section aria-labelledby="d-luu">
          <h2 id="d-luu">Lưu ở đâu</h2>
          <p>Cơ sở dữ liệu ở Neon (Singapore). Máy chủ chạy ở Render (Singapore). Trang web phục vụ qua Vercel.</p>
        </section>
        <section aria-labelledby="d-ai">
          <h2 id="d-ai">HABIT AI xử lý ở đâu</h2>
          {cfg.isPending ? (
            <p className="muted">Đang tải…</p>
          ) : llm ? (
            <p>
              Khi em hỏi, câu hỏi đã lọc thông tin cá nhân được gửi tới dịch vụ AI ({cfg.data?.aiProvider}) để viết lời gợi ý. Dịch vụ này xử lý theo điều khoản của họ. HABIT AI không gửi đáp án và luôn có bước kiểm tra trước khi em đọc.
            </p>
          ) : (
            <p>Hiện HABIT AI chạy bằng các quy tắc có sẵn trên máy chủ của mình. Câu hỏi của em không gửi tới dịch vụ AI nào bên ngoài.</p>
          )}
        </section>
        <section aria-labelledby="d-giu">
          <h2 id="d-giu">Giữ bao lâu, xóa thế nào</h2>
          <p>Không có việc tự động xóa. Sau khi đợt khảo sát kết thúc, nhóm nghiên cứu làm hai việc bằng tay:</p>
          <ul>
            <li>Khóa các tài khoản khách, nên mã khảo sát của em không đăng nhập lại được nữa. Tài khoản khách chưa làm bài nào thì được xóa hẳn.</li>
            <li>Chạy dọn dữ liệu, kiểm tra trước khi chạy thật. Người làm là thầy cô phụ trách và nhóm nghiên cứu. Ngày chạy được ghi vào nhật ký của nhóm.</li>
          </ul>
          <p>
            Câu trả lời bài tập và câu em hỏi HABIT AI không xóa được từng dòng, vì hệ thống chỉ cho thêm, không cho sửa hay xóa. Các dòng này được giữ ẩn danh, chỉ gắn với mã khảo sát (không gắn với tên em) để nhóm dùng cho nghiên cứu. Muốn xóa hết, nhóm phải xóa cả cơ sở dữ liệu của đợt khảo sát.
          </p>
        </section>
        <section aria-labelledby="d-xoa">
          <h2 id="d-xoa">Em muốn xóa dữ liệu của mình</h2>
          <p>
            Em nói với thầy cô phụ trách và đưa mã khảo sát của em. Hiện chưa có chức năng xóa riêng từng mã. Thầy cô ghi nhận yêu cầu của em và báo lại cho nhóm nghiên cứu để nhóm xử lý.
          </p>
        </section>
        <p>
          <Link href="/login">Quay lại</Link>
        </p>
      </div>
    </main>
  );
}
