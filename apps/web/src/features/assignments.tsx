"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, ErrorBox, Field } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { fmtDateTime, localInputToIso, toLocalInput } from "@/lib/format";
import { checkTitle, cleanTitle, TITLE_MAX } from "@/lib/title";

type Assignment = Schemas["AssignmentOut"];

/** Change the due time or cancel one assignment. Cancel is soft: students stop seeing it, answers already given stay. */
export function AssignmentActions({ classId, assignment }: { classId: string; assignment: Assignment }) {
  const qc = useQueryClient();
  const [mode, setMode] = useState<"none" | "due" | "name" | "cancel">("none");
  const [name, setName] = useState(assignment.studentTitle);
  const [due, setDue] = useState(() => toLocalInput(new Date(assignment.dueAt)));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const path = { params: { path: { class_id: classId, assignment_id: assignment.id } } };

  async function run(call: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await call();
      setMode("none");
      await qc.invalidateQueries({ queryKey: ["class-assignments", classId] });
      await qc.invalidateQueries({ queryKey: ["lesson-assignments"] });
    } catch (e) {
      setError(e);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <div className="row-actions">
        <button type="button" className="link-btn" onClick={() => setMode(mode === "due" ? "none" : "due")}>
          Sửa hạn
        </button>
        <button type="button" className="link-btn" onClick={() => setMode(mode === "name" ? "none" : "name")}>
          Đổi tên hiển thị
        </button>
        <button type="button" className="link-btn" onClick={() => setMode(mode === "cancel" ? "none" : "cancel")}>
          Hủy giao
        </button>
      </div>
      <ErrorBox error={error} />
      {mode === "due" ? (
        <form
          className="row"
          onSubmit={(e) => {
            e.preventDefault();
            void run(() => unwrap(api.PATCH("/v1/classes/{class_id}/assignments/{assignment_id}", { ...path, body: { dueAt: localInputToIso(due) } })));
          }}
        >
          <Field label="Hạn nộp mới">
            <input type="datetime-local" required value={due} onChange={(e) => setDue(e.target.value)} />
          </Field>
          <Button type="submit" variant="primary" busy={busy}>
            Lưu hạn
          </Button>
        </form>
      ) : null}
      {mode === "name" ? (
        <form
          className="stack"
          onSubmit={(e) => {
            e.preventDefault();
            if (!checkTitle(name)) void run(() => unwrap(api.PATCH("/v1/classes/{class_id}/assignments/{assignment_id}", { ...path, body: { displayTitle: cleanTitle(name) } })));
          }}
        >
          <Field label="Tên học sinh thấy" hint={checkTitle(name) ?? `${cleanTitle(name).length}/${TITLE_MAX} ký tự. Chỉ đổi tên của bài giao này cho lớp ${assignment.classCode}.`}>
            <input value={name} aria-invalid={checkTitle(name) ? true : undefined} onChange={(e) => setName(e.target.value)} />
          </Field>
          <div className="row-actions">
            <Button type="submit" variant="primary" busy={busy} disabled={!!checkTitle(name)}>
              Lưu tên
            </Button>
            {assignment.displayTitle ? (
              <Button busy={busy} onClick={() => void run(() => unwrap(api.PATCH("/v1/classes/{class_id}/assignments/{assignment_id}", { ...path, body: { displayTitle: null } })))}>
                Về tên của bản đã xuất bản
              </Button>
            ) : null}
          </div>
        </form>
      ) : null}
      {mode === "cancel" ? (
        <div className="alert alert-warning" role="group" aria-label="Xác nhận hủy giao">
          <p>Hủy giao &quot;{assignment.studentTitle}&quot; cho lớp {assignment.classCode}? Học sinh sẽ không thấy bài nữa, câu đã trả lời vẫn được giữ.</p>
          <div className="row-actions">
            <Button variant="primary" busy={busy} onClick={() => void run(() => unwrap(api.DELETE("/v1/classes/{class_id}/assignments/{assignment_id}", path)))}>
              Xác nhận hủy giao
            </Button>
            <Button onClick={() => setMode("none")}>Không hủy</Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

/** "Đã giao cho: 10A1 (hạn …)" on the lesson page. Nothing when the lesson is not assigned. */
export function LessonAssignments({ lessonId }: { lessonId: string }) {
  const q = useQuery({
    queryKey: ["lesson-assignments", lessonId],
    queryFn: () => unwrap(api.GET("/v1/lessons/{lesson_id}/assignments", { params: { path: { lesson_id: lessonId } } })),
  });
  const items = q.data?.items ?? [];
  if (items.length === 0) return null;
  return (
    <p className="muted small" aria-label="Lớp đã được giao bài này">
      Đã giao cho:{" "}
      {items.map((a, i) => (
        <span key={a.id}>
          {i ? "; " : ""}
          <a href={`/classes?class=${a.classId}`}>{a.classCode}</a> (hạn {fmtDateTime(a.dueAt)})
        </span>
      ))}
    </p>
  );
}
