"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { Button, ErrorBox, Field, Loading } from "@/components/ui";
import { GUEST_NOTICE } from "@/features/guest";
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
  const [guestBusy, setGuestBusy] = useState(false);
  const [code, setCode] = useState("");
  const cfg = useQuery({ queryKey: ["auth-config"], queryFn: () => unwrap(api.GET("/v1/auth/config")), retry: false });
  const guest = cfg.data?.guestEnabled === true;

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

  async function enterAsGuest() {
    setGuestBusy(true);
    setError(null);
    try {
      const g = code.trim()
        ? await unwrap(api.POST("/v1/auth/guest/resume", { body: { surveyCode: code.trim() } }))
        : await unwrap(api.POST("/v1/auth/guest", { body: {} }));
      qc.setQueryData(ME_KEY, g.user);
      router.replace("/student");
    } catch (err) {
      setError(err);
      setGuestBusy(false);
    }
  }

  const accountFields = (
    <>
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
    </>
  );

  // method="post": if JS has not loaded yet, a native submit must never put the password in the URL.
  return (
    <form className="card login-card" method="post" onSubmit={submit}>
      <p className="login-brand">◉ <span>PreClass AI</span></p>
      <p className="eyebrow">MỖI CÂU HỎI LÀ MỘT KHÁM PHÁ</p>
      <h1>Chào mừng trở lại!</h1>
      <p className="muted">Đăng nhập để tiếp tục hành trình Địa lí của em.</p>
      <ErrorBox error={error} />
      {cfg.isPending ? (
        <Loading /> // do not flash the account form and then collapse it when guest access turns out to be on
      ) : guest ? (
        <>
          <div className="stack">
            <Button type="button" variant="primary" className="btn-lg" busy={guestBusy} onClick={() => void enterAsGuest()}>
              Vào làm thử (không cần tài khoản)
            </Button>
            <p className="muted small">{GUEST_NOTICE}</p>
          </div>
          <details className="login-more">
            <summary>Giáo viên / có tài khoản</summary>
            <div className="stack">{accountFields}</div>
          </details>
          <details className="login-more">
            <summary>Đã có mã khảo sát?</summary>
            <div className="stack">
              <Field label="Mã khảo sát" hint="Dạng KS-XXXX, hiện ở đầu trang bài làm.">
                <input name="surveyCode" autoComplete="off" value={code} onChange={(e) => setCode(e.target.value)} placeholder="KS-7H4P" />
              </Field>
              <Button type="button" busy={guestBusy} disabled={!code.trim()} onClick={() => void enterAsGuest()}>
                Vào lại bằng mã
              </Button>
            </div>
          </details>
        </>
      ) : (
        accountFields
      )}
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
