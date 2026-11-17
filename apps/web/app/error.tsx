"use client";

import { useEffect } from "react";

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error(error);
  }, [error]);
  return (
    <main className="login-page">
      <div className="card login-card" role="alert">
        <h1>Đã có lỗi xảy ra</h1>
        <p className="muted">Trang gặp lỗi không mong muốn. Thử lại, hoặc tải lại trang.</p>
        <button type="button" className="btn btn-primary" onClick={reset}>
          Thử lại
        </button>
      </div>
    </main>
  );
}
