"use client";

import { useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { ErrorBox, Loading } from "@/components/ui";
import { DataDetails, GUEST_NOTICE } from "@/features/guest";
import { api, unwrap } from "@/lib/api";
import { homeFor, ME_KEY, useAuth } from "@/lib/auth";

/** /thu?bai=<slug>: shareable link / QR for students. Creates (or resumes) an anonymous guest and opens the lesson. */
function Start() {
  const lessonKey = useSearchParams().get("bai") ?? undefined;
  const { user, loading } = useAuth();
  const qc = useQueryClient();
  const router = useRouter();
  const [error, setError] = useState<unknown>(null);
  const started = useRef(false);

  useEffect(() => {
    if (loading || started.current) return;
    started.current = true; // one guest per visit, even if React re-runs the effect
    (async () => {
      try {
        const cfg = await unwrap(api.GET("/v1/auth/config"));
        if (user && !user.isGuest) return void router.replace(homeFor(user.role));
        if (!cfg.guestEnabled) return void router.replace("/login");
        const g =
          user?.isGuest && user.surveyCode
            ? await unwrap(api.POST("/v1/auth/guest/resume", { body: { surveyCode: user.surveyCode, lessonKey } }))
            : await unwrap(api.POST("/v1/auth/guest", { body: { lessonKey } }));
        qc.setQueryData(ME_KEY, g.user);
        router.replace(g.assignmentId ? `/student/assignments/${g.assignmentId}` : "/student");
      } catch (err) {
        setError(err);
      }
    })();
  }, [loading, user, lessonKey, qc, router]);

  return (
    <main className="login-page">
      <div className="card login-card">
        <p className="login-brand">
          ◉ <span>PreClass AI</span>
        </p>
        <h1>Đang vào bài…</h1>
        <p className="muted">{GUEST_NOTICE}</p>
        <DataDetails always />
        {error ? (
          <>
            <ErrorBox error={error} />
            <p>
              <Link href="/login">Về trang đăng nhập</Link>
            </p>
          </>
        ) : (
          <Loading label="Đang chuẩn bị bài cho em…" />
        )}
      </div>
    </main>
  );
}

export default function StartPage() {
  return (
    <Suspense>
      <Start />
    </Suspense>
  );
}
