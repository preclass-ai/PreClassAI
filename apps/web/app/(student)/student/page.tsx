"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Badge, Empty, ErrorBox, Loading } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { fmtDate } from "@/lib/format";
import type { Tone } from "@/lib/labels";

const STATUS: Record<Schemas["StudentAssignmentSummary"]["status"], { label: string; tone: Tone }> = {
  NOT_STARTED: { label: "Chưa làm", tone: "info" },
  IN_PROGRESS: { label: "Đang làm", tone: "warning" },
  DONE: { label: "Đã xong", tone: "success" },
  CLOSED: { label: "Hết hạn", tone: "neutral" },
};

export default function StudentHome() {
  const list = useQuery({ queryKey: ["student-assignments"], queryFn: () => unwrap(api.GET("/v1/student/assignments")) });
  const { user } = useAuth();
  // Anonymous survey guests (class KS) have no deadline: do not show the far-future date the class was created with.
  const showDue = (classCode: string) => !user?.isGuest && classCode !== "KS";
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
      <ErrorBox error={list.error} />
      {list.isPending ? (
        <Loading />
      ) : (
        <>
          <div className="student-stats" aria-label="Tổng quan bài học">
            <div className="stat-card"><strong>{assignments.length} bài được giao</strong><span>Bài tập của em</span></div>
            <div className="stat-card"><strong>{unfinished} bài cần làm</strong><span>Cần làm tiếp</span></div>
            <div className="stat-card"><strong>{completed} bài hoàn thành</strong><span>Đã xong</span></div>
          </div>
          <div className="section-heading"><div><h2>Bài được giao</h2></div><span className="muted small">Chọn một bài để bắt đầu</span></div>
          {assignments.length === 0 ? <Empty>Hiện chưa có bài nào được giao. Khi thầy cô giao bài, em sẽ thấy ở đây.</Empty> : null}
          <ul className="assignment-grid plain">
          {assignments.map((a) => {
            const s = STATUS[a.status];
            return (
              <li key={a.id}>
                <Link href={`/student/assignments/${a.id}`} className="card assignment-card">
                  <div className="assignment-top"><span className="assignment-kicker">Địa lí · {a.className ?? a.classCode}</span><Badge tone={s.tone}>{s.label}</Badge></div>
                  <strong className="assignment-title">{a.title}</strong>
                  {showDue(a.classCode) ? <div className="muted small">Hạn nộp {fmtDate(a.dueAt)}</div> : null}
                  <div className="bar" aria-label={`Đã làm ${a.answeredCount}/${a.itemCount} câu`}>
                    <span style={{ width: `${a.itemCount ? (100 * a.answeredCount) / a.itemCount : 0}%` }} />
                  </div>
                  <div className="assignment-foot"><span className="small">Đã làm {a.answeredCount}/{a.itemCount} câu</span><span className="assignment-arrow" aria-hidden="true">↗</span></div>
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
