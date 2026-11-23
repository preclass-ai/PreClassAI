"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import type { CSSProperties } from "react";
import { GardenCard } from "@/features/garden/garden-card";
import { stageFor, type SpeciesId } from "@/features/garden/species";
import { MascotAvatar } from "@/features/garden/tree";
import { useGarden, useProgress } from "@/features/garden/store";
import { GuestBanner } from "@/features/guest";
import { InstallApp } from "@/features/install-app";
import { Badge, Empty, ErrorBox, Loading } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import type { Tone } from "@/lib/labels";
import { useTheme } from "@/lib/theme";

const STATUS: Record<Schemas["StudentAssignmentSummary"]["status"], { label: string; tone: Tone }> = {
  NOT_STARTED: { label: "Chưa làm", tone: "info" },
  IN_PROGRESS: { label: "Đang làm", tone: "warning" },
  DONE: { label: "Đã xong", tone: "success" },
  CLOSED: { label: "Hết hạn", tone: "neutral" },
};

/** Hours from now to a due date, in words ("còn 18 giờ", "còn 3 ngày"). */
function dueIn(dueAt: string, now = Date.now()): { text: string; soon: boolean } {
  const h = (Date.parse(dueAt) - now) / 3_600_000;
  if (h <= 0) return { text: "đã hết hạn", soon: true };
  const text = h < 1 ? "còn dưới 1 giờ" : h < 48 ? `còn ${Math.round(h)} giờ` : `còn ${Math.round(h / 24)} ngày`;
  return { text, soon: h <= 48 };
}

/**
 * Overview strip under the garden: the student's mascot (or a sprout before planting), what is left with a small
 * progress bar, the nearest due date, and the streak once there is one (a "0" streak only discourages).
 */
function StudyStrip({ todo, done }: { todo: number; done: number }) {
  const progress = useProgress();
  const garden = useGarden();
  const next = progress?.pending[0];
  const due = next ? dueIn(next.dueAt) : null;
  const total = todo + done;
  return (
    <div className="student-strip" aria-label="Tổng quan bài tập" data-tour="strip">
      <span className="strip-icon" aria-hidden="true">
        {garden.species ? (
          <MascotAvatar species={garden.species} stage={stageFor(progress?.done ?? 0)} size={46} />
        ) : (
          <svg viewBox="0 0 48 48" width="46" height="46">
            <ellipse cx="24" cy="40" rx="15" ry="4.5" fill="#c08a5a" />
            <ellipse cx="24" cy="38.5" rx="12" ry="3.2" fill="#8a5a36" />
            <path d="M24 38V24" stroke="#5aa64a" strokeWidth="2.6" strokeLinecap="round" />
            <path d="M24 26c0-6 4-10 12-10-.4 7-4.6 10.6-12 10z" fill="#8fd16b" />
            <path d="M24 28c-.4-5.4-4-8.6-10.6-8.6.2 5.8 3.8 8.9 10.6 8.6z" fill="#b5e27a" />
          </svg>
        )}
      </span>
      <span className="strip-main">
        <span className="strip-count">
          <strong>{todo} bài cần làm</strong> <span aria-hidden="true">·</span> {done} bài đã xong
        </span>
        {total ? (
          <span className="strip-bar" role="progressbar" aria-label="Bài đã xong" aria-valuemin={0} aria-valuemax={total} aria-valuenow={done}>
            <span style={{ width: `${(100 * done) / total}%` }} />
          </span>
        ) : null}
      </span>
      <span className="strip-chips">
        {next && due ? (
          <span className={`strip-chip${due.soon ? " soon" : ""}`} title={`Hạn ${fmtDate(next.dueAt)}`}>
            <svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden="true"><circle cx="12" cy="12" r="8.5" /><path d="M12 7.5V12l3 2" /></svg> Gần hạn nhất: <b>{due.text}</b>
          </span>
        ) : todo === 0 && total ? (
          <span className="strip-chip ok"><svg viewBox="0 0 24 24" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12.5l4.5 4.5L19 7.5" /></svg> Xong hết bài rồi!</span>
        ) : null}
        {progress && progress.streak > 0 ? (
          <span className="strip-chip streak"><svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor" aria-hidden="true"><path d="M12 2.5c.6 3.2 4.8 5.6 4.8 10.4A4.8 4.8 0 0 1 12 17.7a4.8 4.8 0 0 1-4.8-4.8c0-2 .9-3.2 1.8-4.3.2 1.6 1 2.7 2.1 3 .2-3.6 1-6.3.9-9.1z" /><path d="M7 19.5h10" stroke="currentColor" strokeWidth="2" strokeLinecap="round" /></svg> {progress.streak} bài liên tiếp</span>
        ) : null}
      </span>
    </div>
  );
}

/**
 * Hero art (public/hero/*.webp, text-free so the heading stays real text): the scene of the seed the student planted.
 * Apple and ginkgo share the knowledge tree's meadow; before planting, the night garden goes with the dark theme.
 */
const HERO_ART: Record<SpeciesId, "knowledge" | "sakura" | "lotus" | "wisteria"> = {
  knowledge: "knowledge",
  sakura: "sakura",
  lotus: "lotus",
  wisteria: "wisteria",
  apple: "knowledge",
  ginkgo: "knowledge",
};

function StudentHero() {
  const species = useGarden().species;
  const { theme } = useTheme();
  const art = species ? HERO_ART[species.id] : theme === "dark" ? "wisteria" : "knowledge";
  return (
    <header className="student-hero hero-banner" data-art={art} style={{ ["--hero-art" as string]: `url(/hero/${art}.webp)` } as CSSProperties}>
      <div className="student-hero-copy">
        <p className="eyebrow hero-eyebrow">
          Hành trình học tập
          <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <path d="M12 21v-9" stroke="#a6dc6c" strokeWidth="2.2" strokeLinecap="round" fill="none" />
            <path d="M12 13c0-4 2.6-6.6 7.5-6.8-.2 4.6-2.9 7.2-7.5 6.8z" fill="#a6dc6c" />
            <path d="M12 14.5c-.3-3.3-2.5-5.4-6.7-5.4.1 3.6 2.3 5.6 6.7 5.4z" fill="#c8ec8f" />
          </svg>
        </p>
        <h1>
          Hôm <span className="hero-mark">nay</span> em <span className="hero-mark">học</span> gì?
        </h1>
        <p>Tự làm trước, rồi xem lời giải thầy cô đã duyệt.</p>
      </div>
    </header>
  );
}

export default function StudentHome() {
  const list = useQuery({ queryKey: ["student-assignments"], queryFn: () => unwrap(api.GET("/v1/student/assignments")) });
  const assignments = list.data?.items ?? [];
  const unfinished = assignments.filter((a) => a.status === "NOT_STARTED" || a.status === "IN_PROGRESS").length;
  const completed = assignments.filter((a) => a.status === "DONE").length;

  return (
    <div className="student-home stack">
      <StudentHero />
      <GuestBanner />
      <GardenCard />
      <ErrorBox error={list.error} />
      {list.isPending ? (
        <Loading />
      ) : (
        <>
          <StudyStrip todo={unfinished} done={completed} />
          <h2 className="section-title">Bài được giao</h2>
          {assignments.length === 0 ? <Empty>Hiện chưa có bài nào được giao. Khi thầy cô giao bài, em sẽ thấy ở đây.</Empty> : null}
          <ul className="assignment-grid plain" data-tour="assignments">
          {assignments.map((a) => {
            const s = STATUS[a.status];
            return (
              <li key={a.id}>
                <Link href={`/student/assignments/${a.id}`} className="card assignment-card">
                  <div className="assignment-top"><span className="assignment-kicker">Địa lí · {a.className ?? a.classCode}</span><Badge tone={s.tone}>{s.label}</Badge></div>
                  <strong className="assignment-title">{a.title}</strong>
                  <div className="muted small">Hạn nộp {fmtDate(a.dueAt)}</div>
                  <div className="assignment-progress">
                    <div className="bar" role="progressbar" aria-valuemin={0} aria-valuemax={a.itemCount} aria-valuenow={a.answeredCount} aria-label="Tiến độ">
                      <span style={{ width: `${a.itemCount ? (100 * a.answeredCount) / a.itemCount : 0}%` }} />
                    </div>
                    <span className="small">{a.answeredCount}/{a.itemCount} câu</span>
                  </div>
                  <span className="assignment-go">{a.status === "DONE" ? "Xem lại" : a.answeredCount > 0 ? "Làm tiếp" : "Làm bài"}</span>
                </Link>
              </li>
            );
          })}
          </ul>
        </>
      )}
      <InstallApp audience="student" />
    </div>
  );
}
