"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { Button, ErrorBox, Field } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { homeFor, ME_KEY, useAuth } from "@/lib/auth";
import { safeNext } from "@/lib/redirect";

function LoginForm() {
  const { user, loading } = useAuth();
  const qc = useQueryClient();
  const router = useRouter();
  const next = safeNext(useSearchParams().get("next"), typeof window === "undefined" ? undefined : window.location.origin);
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    if (!loading && user) router.replace(next ?? homeFor(user.role));
  }, [loading, user, next, router]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const me = await unwrap(api.POST("/v1/auth/login", { body: { identifier: identifier.trim(), password } }), {
        quiet401: true,
      });
      qc.setQueryData(ME_KEY, me);
      router.replace(next ?? homeFor(me.role));
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  // method="post": if JS has not loaded yet, a native submit must never put the password in the URL.
  return (
    <form className="card login-card" method="post" onSubmit={submit}>
      <p className="login-brand">◉ <span>PreClass AI</span></p>
      <p className="eyebrow">MỖI CÂU HỎI LÀ MỘT KHÁM PHÁ</p>
      <h1>Chào mừng trở lại!</h1>
      <p className="muted">Đăng nhập để tiếp tục hành trình Địa lí của em.</p>
      <ErrorBox error={error} />
      <Field label="Email hoặc mã học sinh">
        <input
          name="identifier"
          autoComplete="username"
          required
          value={identifier}
          onChange={(e) => setIdentifier(e.target.value)}
          placeholder="vd: HS10-01"
        />
      </Field>
      <Field label="Mật khẩu">
        <input
          name="password"
          type="password"
          autoComplete="current-password"
          required
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </Field>
      <Button type="submit" variant="primary" busy={busy}>
        Đăng nhập
      </Button>
      <p className="login-footnote">Bài học có nguồn kiểm chứng · Lời giải được thầy cô duyệt</p>
    </form>
  );
}

export default function LoginPage() {
  return (
    <main className="login-page">
      <div className="login-layout">
        <section className="login-story" aria-label="Giới thiệu PreClass AI">
          <div className="login-story-top"><span className="story-symbol" aria-hidden="true">✦</span> ATLAS HỌC TẬP</div>
          <div className="login-story-copy"><p className="eyebrow">HỌC ĐỊA LÍ THEO CÁCH CỦA EM</p><h2>Đi xa hơn cùng mỗi câu hỏi.</h2><p>Đọc, quan sát và kết nối thế giới xung quanh qua những bài học có nguồn rõ ràng.</p></div>
          <div className="atlas-graphic" aria-hidden="true"><span className="atlas-ring atlas-ring-one" /><span className="atlas-ring atlas-ring-two" /><span className="atlas-center">⌖</span><span className="atlas-label atlas-label-one">21° BẮC</span><span className="atlas-label atlas-label-two">105° ĐÔNG</span></div>
          <p className="login-story-bottom">Địa lí 10–11 <span>•</span> Học để hiểu thế giới</p>
        </section>
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
