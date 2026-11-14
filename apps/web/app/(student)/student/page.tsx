"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { Badge, DataNotice, Empty, ErrorBox, Loading } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import type { Tone } from "@/lib/labels";

const STATUS: Record<Schemas["StudentAssignmentSummary"]["status"], { label: string; tone: Tone }> = {
  NOT_STARTED: { label: "Chưa làm", tone: "info" },
  IN_PROGRESS: { label: "Đang làm", tone: "warning" },
  DONE: { label: "Đã xong", tone: "success" },
  CLOSED: { label: "Hết hạn", tone: "neutral" },
};

export default function StudentHome() {
  const list = useQuery({ queryKey: ["student-assignments"], queryFn: () => unwrap(api.GET("/v1/student/assignments")) });
  const assignments = list.data?.items ?? [];
  const unfinished = assignments.filter((a) => a.status === "NOT_STARTED" || a.status === "IN_PROGRESS").length;
  const completed = assignments.filter((a) => a.status === "DONE").length;

  return (
    <div className="student-home stack">
      <header className="student-hero">
        <div className="student-hero-copy">
          <p className="eyebrow">HÀNH TRÌNH ĐỊA LÍ</p>
          <h1>Mỗi bài học là một vùng đất mới</h1>
          <p>Khám phá số liệu, tự tìm câu trả lời rồi xem lời giải thích đã được thầy cô duyệt.</p>
        </div>
        <div className="student-hero-art" aria-hidden="true"><span className="hero-orbit hero-orbit-one" /><span className="hero-orbit hero-orbit-two" /><span className="hero-pin">⌖</span></div>
      </header>
      <DataNotice />
      <ErrorBox error={list.error} />
      {list.isPending ? (
        <Loading />
      ) : (
        <>
          <div className="student-stats" aria-label="Tổng quan bài học">
            <div className="stat-card"><strong>{assignments.length} bài được giao</strong><span>Kho bài Địa lí của em</span></div>
            <div className="stat-card"><strong>{unfinished} bài cần làm</strong><span>Tiếp tục hành trình</span></div>
            <div className="stat-card"><strong>{completed} bài hoàn thành</strong><span>Những nơi đã khám phá</span></div>
          </div>
          <div className="section-heading"><div><p className="eyebrow">BẢN ĐỒ BÀI HỌC</p><h2>Bài được giao</h2></div><span className="muted small">Chọn một bài để bắt đầu</span></div>
          {assignments.length === 0 ? <Empty>Hiện chưa có bài nào được giao. Khi thầy cô giao bài, em sẽ thấy ở đây.</Empty> : null}
          <ul className="assignment-grid plain">
          {assignments.map((a) => {
            const s = STATUS[a.status];
            return (
              <li key={a.id}>
                <Link href={`/student/assignments/${a.id}`} className="card assignment-card">
                  <div className="assignment-top"><span className="assignment-kicker">ĐỊA LÍ · LỚP {a.classCode}</span><Badge tone={s.tone}>{s.label}</Badge></div>
                  <strong className="assignment-title">{a.title}</strong>
                  <div className="muted small">Hạn nộp {fmtDateTime(a.dueAt)}</div>
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
