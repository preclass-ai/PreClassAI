"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { Button, ErrorBox, Loading, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { errorCode } from "@/lib/errors";
import { fmtPercent } from "@/lib/format";
import { SKILL } from "@/lib/labels";

const REFUSAL: Record<string, string> = {
  ANSWER_REQUEST: "Xin đáp án",
  CONFIRM_OPTION: "Hỏi phương án đúng hay sai",
  INJECTION: "Cố đổi cách làm việc của HABIT AI",
  UNSAFE: "Nội dung không phù hợp",
  OFFTOPIC: "Ngoài phạm vi bài",
};

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

      {(d.competencies ?? []).length ? <Heatmap d={d} /> : null}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Câu</th>
              <th>Đúng ngay lần đầu</th>
              <th>Phương án sai hay chọn</th>
              <th>Gợi ý cao nhất</th>
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
                <td>{i.topWrongOption ? `${i.topWrongOption} (${fmtPercent(i.topWrongShare ?? null)})` : "Chưa có"}</td>
                <td>{i.maxHintLevel ? `Bậc ${i.maxHintLevel}` : "Chưa dùng"}</td>
                <td>
                  {i.asks}
                  {i.needsReteach ? <> <span className="badge badge-warning">Cần dạy lại</span></> : null}
                  {(i.questions ?? []).length ? (
                    <details>
                      <summary className="small">Câu hỏi theo câu</summary>
                      <ul className="plain small">
                        {(i.questions ?? []).map((q) => (
                          <li key={q.key}>
                            {q.label} ({q.count}): {q.examples.map((e) => `“${e}”`).join("; ")}
                          </li>
                        ))}
                      </ul>
                    </details>
                  ) : null}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {(d.blockedReasons ?? []).length ? (
        <p className="muted small">
          HABIT AI đã từ chối: {(d.blockedReasons ?? []).map((b) => `${REFUSAL[b.reason] ?? b.reason} (${b.count})`).join("; ")}.
        </p>
      ) : null}
      <div className="row-actions">
        <Button variant="secondary" busy={analyze.isPending} onClick={() => analyze.mutate()}>
          {d.llmAvailable ? "AI phân tích" : "Tóm tắt chủ đề vướng"}
        </Button>
        <Practice insights={d} classId={classId} />
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
            <p className="muted small">{analyze.data.generatedBy === "llm"
                ? "Do AI tóm tắt, thầy cô kiểm tra lại."
                : analyze.data.generatedBy === "replay"
                  ? "Bản ghi sẵn dùng cho trình diễn, chưa phải kết quả chạy trực tiếp."
                  : "Tổng hợp tự động từ câu hỏi và kết quả."}</p>
          </div>
        ) : (
          <Notice>Chưa đủ dữ liệu để tóm tắt.</Notice>
        )
      ) : null}
    </section>
  );
}

/** First-attempt correct rate per item (rows) and competency (columns); each item belongs to one competency. */
function Heatmap({ d }: { d: Schemas["InsightsOut"] }) {
  const cols = d.competencies ?? [];
  const band = (r: number | null | undefined) => (r == null ? "heat-none" : r < 0.4 ? "heat-low" : r < 0.7 ? "heat-mid" : "heat-high");
  return (
    <div className="table-wrap" role="region" aria-label="Bản đồ nhiệt: tỉ lệ đúng ngay lần đầu theo câu và năng lực" tabIndex={0}>
      <table className="heat">
        <caption className="small muted">Tỉ lệ đúng ngay lần đầu theo câu và năng lực</caption>
        <thead>
          <tr>
            <th scope="col">Câu</th>
            {cols.map((c) => (
              <th key={c.code} scope="col">
                {c.name}
              </th>
            ))}
          </tr>
          <tr>
            <th scope="row">Cả năng lực</th>
            {cols.map((c) => (
              <td key={c.code} className={band(c.firstAttemptCorrectRate)}>
                {fmtPercent(c.firstAttemptCorrectRate ?? null)}
              </td>
            ))}
          </tr>
        </thead>
        <tbody>
          {d.items.map((i) => (
            <tr key={i.itemBlockId}>
              <th scope="row">Câu {i.position}</th>
              {cols.map((c) => (
                <td key={c.code} className={c.code === i.competencyCode ? band(i.firstAttemptCorrectRate) : "heat-empty"}>
                  {c.code === i.competencyCode ? fmtPercent(i.firstAttemptCorrectRate ?? null) : ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** Draft extra practice with the existing Generate pipeline: AI proposes, validation runs, the teacher approves like any block. */
function Practice({ insights: d, classId }: { insights: Schemas["InsightsOut"]; classId: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  if (!d.canPractice || (d.focusSkills.length === 0 && (d.reteachItemIds ?? []).length === 0)) return null;

  async function reteach() {
    setBusy(true);
    setError(null);
    try {
      const r = await unwrap(api.POST("/v1/classes/{class_id}/assignments/{assignment_id}/insights/reteach", { params: { path: { class_id: classId, assignment_id: d.assignmentId } } }));
      if (d.focusSkills.length && !r.alreadyExists) {  // a draft already covers these passages: open it, do not add more
        await unwrap(
          api.POST("/v1/lessons/{lesson_id}/generate", {
            params: { path: { lesson_id: d.lessonId } },
            body: { outputType: "WORKSHEET", nItems: 3, focusSkills: d.focusSkills, mode: "append" },
          }),
        );
      }
      router.push(`/lessons/${d.lessonId}?tab=editor`);
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

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
      {(d.reteachItemIds ?? []).length ? (
        <Button variant="primary" busy={busy} onClick={() => void reteach()}>
          Đề xuất dạy lại
        </Button>
      ) : null}
      <Button variant={(d.reteachItemIds ?? []).length ? "secondary" : "primary"} busy={busy} onClick={() => void run()}>
        AI gợi ý bài tập thêm
      </Button>
      <ErrorBox error={error} />
      <span className="muted small">Tạo bản nháp 3 câu về {d.focusSkills.map((s) => SKILL[s]).join(", ")}. Thầy cô duyệt rồi mới giao.</span>
    </>
  );
}

