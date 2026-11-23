"use client";

import { useState, type FormEvent } from "react";
import { Button, ErrorBox, Field, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { checkTitle, cleanTitle, TITLE_MAX } from "@/lib/title";
import { useRefreshLesson } from "./lesson-data";

type Lesson = Schemas["LessonOut"];

/** "Tên bài" and "Mục tiêu" of the lesson (PATCH /lessons/{id}, logged in the history). The published version keeps its own frozen name. */
export function LessonTitleForm({ lesson }: { lesson: Lesson }) {
  const refresh = useRefreshLesson(lesson.id);
  const [title, setTitle] = useState(lesson.title);
  const [goal, setGoal] = useState(lesson.goal ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState(false);
  const problem = checkTitle(title);
  const changed = cleanTitle(title) !== lesson.title || goal.trim() !== (lesson.goal ?? "");
  const published = lesson.publishedVersionId != null || lesson.currentRevision.state !== "DRAFT";

  async function save(e: FormEvent) {
    e.preventDefault();
    if (problem) return;
    setBusy(true);
    setError(null);
    setSaved(false);
    try {
      await unwrap(api.PATCH("/v1/lessons/{lesson_id}", { params: { path: { lesson_id: lesson.id } }, body: { title: cleanTitle(title), goal: goal.trim() } }));
      await refresh();
      setSaved(true);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card stack" onSubmit={(e) => void save(e)} aria-label="Thông tin bài học">
      <Field label="Tên bài" hint={problem ?? `${cleanTitle(title).length}/${TITLE_MAX} ký tự`}>
        <input value={title} maxLength={TITLE_MAX + 40} aria-invalid={problem ? true : undefined} onChange={(e) => { setTitle(e.target.value); setSaved(false); }} />
      </Field>
      <Field label="Mục tiêu">
        <textarea rows={2} maxLength={500} value={goal} onChange={(e) => { setGoal(e.target.value); setSaved(false); }} />
      </Field>
      {published ? (
        <Notice tone="info">
          Tên mới áp dụng khi xuất bản bản tiếp theo. Bài đã giao vẫn hiện tên cũ với học sinh; muốn đổi ngay, dùng &quot;Đổi tên hiển thị&quot; ở trang Lớp &amp; bài giao.
        </Notice>
      ) : null}
      <ErrorBox error={error} />
      <div className="row-actions">
        <Button type="submit" variant="primary" busy={busy} disabled={!changed || !!problem}>
          Lưu
        </Button>
        {saved ? <span role="status" className="muted small">Đã lưu</span> : null}
      </div>
    </form>
  );
}
