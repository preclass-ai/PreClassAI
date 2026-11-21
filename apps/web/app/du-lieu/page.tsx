"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api, unwrap } from "@/lib/api";

/** "Dữ liệu của em đi đâu": public, short, written for students. Places and the 90-day period are the team's decisions (see docs/security/PHAP-LY-DU-LIEU.md). */
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
          <h2 id="d-giu">Giữ bao lâu</h2>
          <p>90 ngày sau khi đợt khảo sát kết thúc, dữ liệu được xóa.</p>
        </section>
        <section aria-labelledby="d-xoa">
          <h2 id="d-xoa">Em muốn xóa dữ liệu của mình</h2>
          <p>Em nói với thầy cô phụ trách và đưa mã khảo sát của em. Thầy cô sẽ xóa các dòng có mã đó.</p>
        </section>
        <p>
          <Link href="/login">Quay lại</Link>
        </p>
      </div>
    </main>
  );
}
