"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { Button, Empty, ErrorBox, Field, Loading, PageHeader } from "@/components/ui";
import { api, unwrap } from "@/lib/api";
import { RequireRole } from "@/lib/auth";
import { refresh } from "@/lib/query";

const TEACHER = ["TEACHER"] as const;

function NewLessonForm() {
  const router = useRouter();
  const qc = useQueryClient();
  const sources = useQuery({ queryKey: ["sources"], queryFn: () => unwrap(api.GET("/v1/sources")) });
  const [title, setTitle] = useState("");
  const [grade, setGrade] = useState<10 | 11>(10);
  const [goal, setGoal] = useState("");
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  function toggle(id: string) {
    setPicked((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const lesson = await unwrap(
        api.POST("/v1/lessons", {
          body: { title: title.trim(), grade, goal: goal.trim() || null, sourceRevisionIds: [...picked] },
        }),
      );
      await refresh(qc, { queryKey: ["lessons"] });
      router.push(`/lessons/${lesson.id}?tab=editor`);
    } catch (err) {
      setError(err);
      setBusy(false);
    }
  }

  const ready = sources.data?.items.filter((s) => s.latestRevision.extractStatus === "OK") ?? [];

  return (
    <>
      <p className="crumbs">
        <Link href="/lessons">← Bài học</Link>
      </p>
      <PageHeader title="Tạo bài mới" sub="Chọn tài liệu gốc để AI soạn bài từ đó." />
      <form className="card stack" onSubmit={submit}>
        <ErrorBox error={error} />
        <div className="row">
          <Field label="Tên bài">
            <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
          </Field>
          <Field label="Khối lớp">
            <select value={grade} onChange={(e) => setGrade(Number(e.target.value) as 10 | 11)}>
              <option value={10}>Lớp 10</option>
              <option value={11}>Lớp 11</option>
            </select>
          </Field>
        </div>
        <Field label="Mục tiêu bài (không bắt buộc)">
          <textarea rows={2} value={goal} onChange={(e) => setGoal(e.target.value)} />
        </Field>
        <fieldset className="stack">
          <legend className="field-label">Nguồn ({picked.size} đã chọn)</legend>
          {sources.isPending ? (
            <Loading />
          ) : ready.length === 0 ? (
            <Empty>
              Chưa có nguồn đọc được. <Link href="/sources">Thêm nguồn</Link> trước.
            </Empty>
          ) : (
            ready.map((s) => (
              <label key={s.id} className="check">
                <input
                  type="checkbox"
                  checked={picked.has(s.latestRevision.id)}
                  onChange={() => toggle(s.latestRevision.id)}
                />
                <span>
                  {s.title} <span className="muted small">v{s.latestRevision.version} · {s.latestRevision.anchorCount} đoạn</span>
                </span>
              </label>
            ))
          )}
        </fieldset>
        <div>
          <Button type="submit" variant="primary" busy={busy} disabled={picked.size === 0}>
            Tạo bài
          </Button>
        </div>
      </form>
    </>
  );
}

export default function NewLessonPage() {
  return (
    <RequireRole roles={TEACHER}>
      <NewLessonForm />
    </RequireRole>
  );
}
