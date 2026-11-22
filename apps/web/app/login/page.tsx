"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState, type FormEvent } from "react";
import { Button, ErrorBox, Field, Loading } from "@/components/ui";
import { DataLink, GUEST_NOTICE } from "@/features/guest";
import { api, ApiError, unwrap } from "@/lib/api";
import { homeFor, ME_KEY, useAuth } from "@/lib/auth";
import { withTimeout, useAfter } from "@/lib/http";
import { safeNext } from "@/lib/redirect";

const WRONG_CODE = "Mã khảo sát không đúng. Em kiểm tra lại mã ở đầu trang bài làm (dạng KS-XXXX).";

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
  const [codeError, setCodeError] = useState<string | null>(null);
  // The config decides whether to show the guest button. It must never block the sign-in form: 15 s timeout, no retry.
  const cfg = useQuery({
    queryKey: ["auth-config"],
    queryFn: ({ signal }) => unwrap(api.GET("/v1/auth/config", { signal: withTimeout(15_000, signal) })),
    retry: false,
  });
  const waited = useAfter(cfg.isPending, 3_000); // slow config: show the account form anyway
  const gaveUp = useAfter(cfg.isPending, 20_000); // hard cap: error state with a retry button
  const configFailed = cfg.isError || gaveUp;
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
    const resume = code.trim();
    setGuestBusy(true);
    setError(null);
    setCodeError(null);
    try {
      const g = resume
        ? await unwrap(api.POST("/v1/auth/guest/resume", { body: { surveyCode: resume } }))
        : await unwrap(api.POST("/v1/auth/guest", { body: {} }));
      qc.setQueryData(ME_KEY, g.user);
      router.replace("/student");
    } catch (err) {
      // A wrong or malformed code belongs next to the code field, not in the generic "not found" box.
      const c = err instanceof ApiError ? err.problem.code : undefined;
      if (resume && (c === "NOT_FOUND" || c === "VALIDATION_ERROR")) setCodeError(WRONG_CODE);
      else setError(err);
      setGuestBusy(false);
    }
  }

  function submitCode(e: FormEvent) {
    e.preventDefault(); // its own form: Enter here must never submit the (collapsed) account form
    if (code.trim()) void enterAsGuest();
  }

  // method="post": if JS has not loaded yet, a native submit must never put the password in the URL.
  const accountFields = (
    <form className="stack" method="post" onSubmit={submit}>
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
    </form>
  );

  return (
    <div className="card login-card">
      <p className="login-brand">◉ <span>PreClass AI</span></p>
      <h1>Chào mừng trở lại!</h1>
      <p className="muted">Đăng nhập để tiếp tục hành trình học tập của em.</p>
      <ErrorBox error={error} />
      {cfg.isPending && !waited ? (
        <Loading /> // brief: avoids flashing the account form and then collapsing it when guest access is on
      ) : configFailed ? (
        <>
          <div className="alert alert-warning" role="status">
            Máy chủ đang khởi động, thử lại sau ít giây.{" "}
            <Button type="button" onClick={() => void cfg.refetch()}>
              Thử lại
            </Button>
          </div>
          {accountFields}
        </>
      ) : guest ? (
        <>
          <div className="stack">
            <Button type="button" variant="primary" className="btn-lg" busy={guestBusy} onClick={() => void enterAsGuest()}>
              Vào làm thử (không cần tài khoản)
            </Button>
            <p className="muted small">{GUEST_NOTICE} <DataLink /></p>
          </div>
          <details className="login-more">
            <summary>Giáo viên / có tài khoản</summary>
            {accountFields}
          </details>
          <details className="login-more">
            <summary>Đã có mã khảo sát?</summary>
            <form className="stack" onSubmit={submitCode}>
              <Field label="Mã khảo sát" hint="Dạng KS-XXXX, hiện ở đầu trang bài làm.">
                <input
                  name="surveyCode"
                  autoComplete="off"
                  value={code}
                  onChange={(e) => {
                    setCode(e.target.value);
                    setCodeError(null);
                  }}
                  placeholder="KS-7H4P"
                  aria-invalid={codeError ? true : undefined}
                  aria-describedby={codeError ? "survey-code-error" : undefined}
                />
              </Field>
              {codeError ? (
                <p id="survey-code-error" className="field-error" role="alert">
                  {codeError}
                </p>
              ) : null}
              <Button type="submit" busy={guestBusy} disabled={!code.trim()}>
                Vào lại bằng mã
              </Button>
            </form>
          </details>
        </>
      ) : (
        <>
          {cfg.isPending ? <p className="muted small">Đang kiểm tra chế độ vào làm thử…</p> : null}
          {accountFields}
        </>
      )}
    </div>
  );
}

export default function LoginPage() {
  return (
    <main className="login-page">
      <div className="login-layout">
        <section className="login-story" aria-label="Giới thiệu PreClass AI">
          <div className="login-story-top"><span className="story-symbol" aria-hidden="true">✦</span> Gia sư AI cá nhân</div>
          <div className="login-story-copy"><p className="eyebrow">Cùng học</p><h2>Làm bài trước, hiểu bài sau.</h2><p>Em tự làm, xin gợi ý khi cần, rồi xem lời giải thầy cô đã duyệt.</p></div>
          <div className="atlas-graphic" aria-hidden="true"><span className="atlas-ring atlas-ring-one" /><span className="atlas-ring atlas-ring-two" /><span className="atlas-center">✦</span></div>
        </section>
        <Suspense>
          <LoginForm />
        </Suspense>
      </div>
    </main>
  );
}
