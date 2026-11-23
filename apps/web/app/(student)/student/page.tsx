"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { GardenCard } from "@/features/garden/garden-card";
import { useGarden, useProgress } from "@/features/garden/store";
import { GuestBanner } from "@/features/guest";
import { Badge, Empty, ErrorBox, Loading } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import type { Tone } from "@/lib/labels";

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

export default function StudentHome() {
  const list = useQuery({ queryKey: ["student-assignments"], queryFn: () => unwrap(api.GET("/v1/student/assignments")) });
  const assignments = list.data?.items ?? [];
  const unfinished = assignments.filter((a) => a.status === "NOT_STARTED" || a.status === "IN_PROGRESS").length;
  const completed = assignments.filter((a) => a.status === "DONE").length;

  return (
    <div className="student-home stack">
      <header className="student-hero">
        <div className="student-hero-copy">
          <p className="eyebrow">Hành trình học tập</p>
          <h1>Hôm nay em học gì?</h1>
          <p>Tự làm trước, rồi xem lời giải thầy cô đã duyệt.</p>
        </div>
        <div className="student-hero-art" aria-hidden="true"><span className="hero-orbit hero-orbit-one" /><span className="hero-orbit hero-orbit-two" /><span className="hero-pin">⌖</span></div>
      </header>
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
    </div>
  );
}
