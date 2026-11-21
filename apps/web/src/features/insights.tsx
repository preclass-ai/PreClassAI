"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, ErrorBox, Loading, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { errorCode } from "@/lib/errors";
import { fmtPercent } from "@/lib/format";
import { SKILL } from "@/lib/labels";

/** "Học sinh hỏi gì": questions asked to HABIT AI, grouped, anonymous. Teacher of the class only (the server enforces it). */
export function Insights({ classId, assignmentId }: { classId: string; assignmentId: string }) {
  const path = { class_id: classId, assignment_id: assignmentId };
  const data = useQuery({
    queryKey: ["insights", classId, assignmentId],
    queryFn: () => unwrap(api.GET("/v1/classes/{class_id}/assignments/{assignment_id}/insights", { params: { path } })),
  });
  const analyze = useMutation({
    mutationFn: () => unwrap(api.POST("/v1/classes/{class_id}/assignments/{assignment_id}/insights/analyze", { params: { path } })),
  });
  if (data.isPending) return <Loading />;
  if (!data.data) return <ErrorBox error={data.error} />;
  const d = data.data;

  return (
    <section className="insights stack" aria-labelledby={`ins-${assignmentId}`}>
      <h3 id={`ins-${assignmentId}`}>Học sinh hỏi gì</h3>
      {d.totalQuestions === 0 ? (
        <p className="muted">Chưa có em nào hỏi HABIT AI ở bài này. Câu hỏi hiện ở đây, đã ẩn danh và bỏ thông tin cá nhân.</p>
      ) : (
        <>
          <p className="muted small">
            {d.totalQuestions} câu hỏi từ {d.askingStudents}/{d.studentCount} học sinh. Không hiện tên hay mã của học sinh.
          </p>
          <ul className="insight-themes plain">
            {d.themes.map((t) => (
              <li key={t.key}>
                <strong>{t.label}</strong> <span className="badge badge-info">{t.count}</span>
                <div className="muted small">Ví dụ: {t.examples.map((e) => `“${e}”`).join("; ")}</div>
              </li>
            ))}
          </ul>
        </>
      )}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Câu</th>
              <th>Đúng ngay lần đầu</th>
              <th>Gợi ý đã dùng</th>
              <th>Câu hỏi cho HABIT AI</th>
            </tr>
          </thead>
          <tbody>
            {d.items.map((i) => (
              <tr key={i.itemBlockId}>
                <td>
                  {i.position}. {i.stem} <span className="muted small">({SKILL[i.skill]})</span>
                </td>
                <td>{fmtPercent(i.firstAttemptCorrectRate)}</td>
                <td>{i.hintsUsed}</td>
                <td>{i.asks}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="row-actions">
        <Button variant="secondary" busy={analyze.isPending} onClick={() => analyze.mutate()}>
          {d.llmAvailable ? "AI phân tích" : "Tóm tắt chủ đề vướng"}
        </Button>
        <Practice insights={d} />
      </div>
      <ErrorBox error={analyze.error} />
      {analyze.data ? (
        analyze.data.topics.length ? (
          <div className="card inset" role="status">
            <strong>Học sinh hay vướng ở đây</strong>
            <ul>
              {analyze.data.topics.map((t) => (
                <li key={t}>{t}</li>
              ))}
            </ul>
            <p className="muted small">{analyze.data.generatedBy === "llm" ? "Do AI tóm tắt, thầy cô kiểm tra lại." : "Tổng hợp tự động từ câu hỏi và kết quả."}</p>
          </div>
        ) : (
          <Notice>Chưa đủ dữ liệu để tóm tắt.</Notice>
        )
      ) : null}
    </section>
  );
}

/** Draft extra practice with the existing Generate pipeline: AI proposes, validation runs, the teacher approves like any block. */
function Practice({ insights: d }: { insights: Schemas["InsightsOut"] }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  if (!d.canPractice || d.focusSkills.length === 0) return null;

  async function run() {
    setBusy(true);
    setError(null);
    try {
      try {
        await unwrap(api.POST("/v1/revisions/{revision_id}/new-revision", { params: { path: { revision_id: d.publishedRevisionId } } }));
      } catch (e) {
        if (errorCode(e) !== "DRAFT_EXISTS") throw e; // a draft already exists: add the practice to it
      }
      await unwrap(
        api.POST("/v1/lessons/{lesson_id}/generate", {
          params: { path: { lesson_id: d.lessonId } },
          body: { outputType: "WORKSHEET", nItems: 3, focusSkills: d.focusSkills, mode: "append" },
        }),
      );
      router.push(`/lessons/${d.lessonId}?tab=editor`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="primary" busy={busy} onClick={() => void run()}>
        AI gợi ý bài tập thêm
      </Button>
      <ErrorBox error={error} />
      <span className="muted small">Tạo bản nháp 3 câu về {d.focusSkills.map((s) => SKILL[s]).join(", ")}. Thầy cô duyệt rồi mới giao.</span>
    </>
  );
}

