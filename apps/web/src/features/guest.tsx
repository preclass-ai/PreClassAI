"use client";

import { useState } from "react";
import { useAuth } from "@/lib/auth";

/** Shown to the person before an anonymous account is created (login page and /thu). */
export const GUEST_NOTICE =
  "Không thu tên hay email. Kết quả làm bài chỉ dùng cho nghiên cứu và không gắn với danh tính của em.";

// Only an https link is ever rendered as a href (a mistyped javascript: value must not become a link).
const RAW_SURVEY_URL = process.env.NEXT_PUBLIC_SURVEY_URL ?? "";
const SURVEY_URL = /^https:\/\//i.test(RAW_SURVEY_URL) ? RAW_SURVEY_URL : "";

function CopyCode({ code }: { code: string }) {
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
    <button type="button" className="btn btn-secondary" onClick={() => void copy()} aria-label={`Sao chép mã khảo sát ${code}`}>
      {copied ? "Đã sao chép" : "Sao chép"}
    </button>
  );
}

/** Small banner for anonymous guests: the code they write on the questionnaire. Nothing for normal accounts. */
export function GuestBanner() {
  const { user } = useAuth();
  if (!user?.isGuest || !user.surveyCode) return null;
  return (
    <div className="alert alert-info guest-banner" role="status">
      <span>
        Mã khảo sát của em: <strong className="guest-code">{user.surveyCode}</strong> — ghi mã này vào phiếu khảo sát.
      </span>
      <CopyCode code={user.surveyCode} />
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
