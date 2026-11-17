import Link from "next/link";

export default function NotFound() {
  return (
    <main className="login-page">
      <div className="card login-card">
        <h1>Không tìm thấy trang</h1>
        <Link className="btn btn-primary" href="/">
          Về trang chính
        </Link>
      </div>
    </main>
  );
}
