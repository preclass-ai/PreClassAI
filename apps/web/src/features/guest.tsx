"use client";

import Link from "next/link";
import { useState } from "react";
import { useAuth } from "@/lib/auth";

/** Shown to the person before an anonymous account is created (login page and /thu). */
export const GUEST_NOTICE =
  "PreClass AI không yêu cầu họ tên hay email. Kết quả làm bài chỉ dùng cho nghiên cứu và không gắn với danh tính của em.";

/** Short answer in a dropdown, with the link to the full page. In the student area guests only: /du-lieu describes the
 * anonymous survey, not school accounts (those have a name and a class). `always` is for the login and /thu pages, where
 * the person has not signed in yet and the text is about the anonymous way in. */
export function DataDetails({ always = false }: { always?: boolean }) {
  const { user } = useAuth();
  if (!always && !user?.isGuest) return null;
  return (
    <details className="login-more">
      <summary>Dữ liệu của em đi đâu?</summary>
      <div className="stack">
        <p>
          Mình lưu mã khảo sát, câu trả lời của em, số lần em xin gợi ý và câu em hỏi HABIT AI (số điện thoại, email, địa
          chỉ được lọc bỏ trước khi lưu). Thầy cô xem số liệu chung của cả lớp và một số câu hỏi không kèm tên, không xem
          bài làm của riêng em.
        </p>
        <DataLink>Xem đầy đủ</DataLink>
      </div>
    </details>
  );
}

/** Link to the page that says what is collected, where it is stored and for how long. */
export function DataLink({ children = "Dữ liệu của em đi đâu" }: { children?: string }) {
  return (
    <Link href="/du-lieu" className="small">
      {children}
    </Link>
  );
}

// Only an https link is ever rendered as a href (a mistyped javascript: value must not become a link).
const RAW_SURVEY_URL = process.env.NEXT_PUBLIC_SURVEY_URL ?? "";
const SURVEY_URL = /^https:\/\//i.test(RAW_SURVEY_URL) ? RAW_SURVEY_URL : "";

function CopyCode({ code, compact = false }: { code: string; compact?: boolean }) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard blocked (http, old browser): the code stays visible to copy by hand */
    }
  }
  return (
    <button type="button" className={compact ? "guest-copy" : "btn btn-secondary"} onClick={() => void copy()} aria-label={`Sao chép mã khảo sát ${code}`}>
      {compact ? (
        <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="9" y="9" width="11" height="11" rx="2" />
          <path d="M5 15V6a2 2 0 0 1 2-2h9" />
        </svg>
      ) : null}
      <span role="status">{copied ? "Đã chép" : compact ? "" : "Sao chép"}</span>
    </button>
  );
}

/** One slim line with the code the student writes on the questionnaire. Nothing for normal accounts. */
export function GuestBanner() {
  const { user } = useAuth();
  if (!user?.isGuest || !user.surveyCode) return null;
  return (
    <div className="guest-chip">
      <span>
        Mã khảo sát: <strong className="guest-code">{user.surveyCode}</strong>
      </span>
      <CopyCode code={user.surveyCode} compact />
    </div>
  );
}

/** End of a worksheet: the code again, plus the questionnaire link when NEXT_PUBLIC_SURVEY_URL is set. */
export function GuestSurveyCard() {
  const { user } = useAuth();
  if (!user?.isGuest || !user.surveyCode) return null;
  return (
    <section className="card guest-survey stack" aria-labelledby="guest-survey-title">
      <h2 id="guest-survey-title">Cảm ơn em đã làm bài!</h2>
      <p>
        Mã khảo sát của em: <strong className="guest-code">{user.surveyCode}</strong>. Hãy ghi mã này vào phiếu khảo sát.
      </p>
      <div className="row-actions">
        <CopyCode code={user.surveyCode} />
        {SURVEY_URL ? (
          <a className="btn btn-primary" href={SURVEY_URL} target="_blank" rel="noopener noreferrer">
            Mở phiếu khảo sát
          </a>
        ) : null}
      </div>
    </section>
  );
}
