"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import type { CSSProperties } from "react";
import { GardenCard } from "@/features/garden/garden-card";
import type { SpeciesId } from "@/features/garden/species";
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

/** One line: what is left, and the assignment streak (only before a tree is planted: the garden shows it then). */
function StudyStrip({ todo, done }: { todo: number; done: number }) {
  const progress = useProgress();
  const planted = !!useGarden().species;
  return (
    <div className="student-strip" aria-label="Tổng quan bài tập" data-tour="strip">
      <span>
        <strong>{todo} bài cần làm</strong> <span aria-hidden="true">·</span> {done} bài đã xong
      </span>
      {progress && !planted ? (
        <span className="strip-habit">
          <span aria-hidden="true">🔥</span> {progress.streak} bài liên tiếp
        </span>
      ) : null}
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
