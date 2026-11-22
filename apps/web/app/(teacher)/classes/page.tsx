"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useState } from "react";
import { Empty, ErrorBox, Loading, PageHeader } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { AssignmentActions } from "@/features/assignments";
import { Insights } from "@/features/insights";
import { RequireRole } from "@/lib/auth";
import { fmtDateTime, fmtPercent } from "@/lib/format";

const TEACHER = ["TEACHER"] as const;

function ClassesView() {
  const router = useRouter();
  const params = useSearchParams();
  const classes = useQuery({ queryKey: ["classes"], queryFn: () => unwrap(api.GET("/v1/classes")) });
  const classId = params.get("class") ?? classes.data?.items[0]?.id ?? null;
  const assignments = useQuery({
    queryKey: ["class-assignments", classId],
    enabled: !!classId,
    queryFn: () =>
      unwrap(api.GET("/v1/classes/{class_id}/assignments", { params: { path: { class_id: classId! } } })),
  });
  const [open, setOpen] = useState<string | null>(null);

  return (
    <>
      <PageHeader
        title="Lớp & bài giao"
        sub="Xem lớp làm bài đến đâu. Trên trang là số liệu của cả lớp; tệp kết quả tải về ghi bài làm theo mã học sinh, không có họ tên."
        actions={
          <Link className="btn btn-primary" href="/lessons">
            Giao bài mới
          </Link>
        }
      />
      <ErrorBox error={classes.error} />
      {classes.isPending ? (
        <Loading />
      ) : (
        <nav className="tabs" aria-label="Lớp">
          {classes.data?.items.map((c) => (
            <button
              key={c.id}
              type="button"
              className={c.id === classId ? "tab on" : "tab"}
              onClick={() => router.replace(`?class=${c.id}`, { scroll: false })}
            >
              {c.code}{c.isSurvey ? " (khảo sát)" : ""} · lớp {c.grade} · {c.studentCount} HS
            </button>
          ))}
        </nav>
      )}
      <ErrorBox error={assignments.error} />
      {assignments.isPending && classId ? (
        <Loading />
      ) : assignments.data?.items.length === 0 ? (
        <Empty>Lớp chưa có bài giao. Giao bài từ tab &quot;Xuất bản & giao bài&quot; của một bài đã xuất bản.</Empty>
      ) : (
        <ul className="stack plain">
          {assignments.data?.items.map((a) => (
            <li key={a.id} className="card">
              <div className="section-head">
                <div>
                  <h2>
                    <Link href={`/lessons/${a.lessonId}`}>{a.lessonTitle}</Link>
                  </h2>
                  <p className="muted small">
                    Giao từ Bản #{a.revisionNo} · Mở {fmtDateTime(a.openAt)} · hạn {fmtDateTime(a.dueAt)} ·{" "}
                    <Link href={`/lessons/${a.lessonId}?tab=publish`}>Mở phần giao bài</Link>
                  </p>
                </div>
                <button type="button" className="link-btn" onClick={() => setOpen(open === a.id ? null : a.id)}>
                  {open === a.id ? "Ẩn tiến độ" : "Xem tiến độ và câu hỏi"}
                </button>
              </div>
              {classId ? <AssignmentActions classId={classId} assignment={a} /> : null}
              {open === a.id && classId ? (
                <>
                  <Progress classId={classId} assignmentId={a.id} />
                  <Insights classId={classId} assignmentId={a.id} />
                </>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </>
  );
}

function Progress({ classId, assignmentId }: { classId: string; assignmentId: string }) {
  const progress = useQuery({
    queryKey: ["progress", classId, assignmentId],
    queryFn: () =>
      unwrap(
        api.GET("/v1/classes/{class_id}/assignments/{assignment_id}/progress", {
          params: { path: { class_id: classId, assignment_id: assignmentId } },
        }),
      ),
  });
  if (progress.isPending) return <Loading />;
  if (!progress.data) return <ErrorBox error={progress.error} />;
  const p = progress.data;
  // Vercel can go live before the API on Render: an older API has no counts and no results.csv, so show neither.
  const hasCounts = typeof p.completedCount === "number" && typeof p.inProgressCount === "number";
  const notStarted = hasCounts ? Math.max(0, p.studentCount - p.completedCount - p.inProgressCount) : 0;
  return (
    <>
      {hasCounts ? (
        <div className="section-head">
          <div>
            <p className="muted small">
              {p.completedCount}/{p.studentCount} em đã làm xong · {p.inProgressCount} em đang làm · {notStarted} em
              chưa làm
            </p>
          </div>
          <a
            className="btn btn-secondary"
            href={`/v1/classes/${classId}/assignments/${assignmentId}/results.csv`}
            download
          >
            Tải kết quả (CSV)
          </a>
        </div>
      ) : null}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Câu</th>
              <th>Đã trả lời</th>
              <th>Đúng ngay lần đầu</th>
            </tr>
          </thead>
          <tbody>
            {p.items.map((i, idx) => (
              <tr key={i.itemBlockId}>
                <td>
                  {idx + 1}. {i.stem}
                </td>
                <td>
                  {i.answeredCount}/{p.studentCount}
                  <div className="bar" aria-hidden="true">
                    <span style={{ width: `${p.studentCount ? (100 * i.answeredCount) / p.studentCount : 0}%` }} />
                  </div>
                </td>
                <td>{fmtPercent(i.firstAttemptCorrectRate)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}

export default function ClassesPage() {
  return (
    <RequireRole roles={TEACHER}>
      <Suspense fallback={<Loading />}>
        <ClassesView />
      </Suspense>
    </RequireRole>
  );
}
