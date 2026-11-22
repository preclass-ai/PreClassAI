"use client";

import { useEffect, useState } from "react";

const STEPS = {
  teacher: [
    "Thêm nguồn hoặc giáo án của thầy cô.",
    "Duyệt từng khối nội dung: chỉ khối đã duyệt mới đến tay học sinh.",
    "Xuất bản rồi giao cho lớp, xem lớp làm bài ở trang Lớp & bài giao.",
  ],
  student: [
    "Ôn nhanh vài thẻ nếu bài có (không tính điểm).",
    "Làm từng câu, cần thì xin gợi ý hoặc hỏi HABIT AI.",
    "Nộp xong sẽ thấy đáp án và lời giải. Bấm Làm lại nếu em muốn luyện thêm.",
  ],
} as const;

const KEY = (role: "teacher" | "student") => `preclass.start.${role}`;

/** "3 bước bắt đầu", closable. The choice is kept in localStorage, which may be blocked: then it shows again next time, nothing breaks. */
export function GettingStarted({ role }: { role: "teacher" | "student" }) {
  const [shown, setShown] = useState(false);
  useEffect(() => {
    let closed = false;
    try {
      closed = localStorage.getItem(KEY(role)) === "closed";
    } catch {
      /* storage blocked: show the box */
    }
    setShown(!closed);
  }, [role]);
  if (!shown) return null;

  function close() {
    setShown(false);
    try {
      localStorage.setItem(KEY(role), "closed");
    } catch {
      /* storage blocked: it comes back next visit */
    }
  }

  return (
    <section className="card getting-started" aria-label="3 bước bắt đầu">
      <div className="section-head">
        <h2>3 bước bắt đầu</h2>
        <button type="button" className="link-btn" onClick={close} aria-label="Đóng khung 3 bước bắt đầu">
          Đóng
        </button>
      </div>
      <ol>
        {STEPS[role].map((s) => (
          <li key={s}>{s}</li>
        ))}
      </ol>
    </section>
  );
}
