"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Button, ErrorBox, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { useRefreshLesson } from "./lesson-data";

/**
 * A pinned source has a newer revision. Switching is explicit (AT-08): affected blocks go to REVIEW_AGAIN and
 * links that cannot be matched become UNRESOLVED.
 */
export function ReplaceSourcesPanel({ lesson }: { lesson: Schemas["LessonOut"] }) {
  const rev = lesson.currentRevision;
  const refresh = useRefreshLesson(lesson.id);
  const [open, setOpen] = useState(false);
  const sources = useQuery({ queryKey: ["sources"], queryFn: () => unwrap(api.GET("/v1/sources")), enabled: open });
  const [picked, setPicked] = useState<Set<string> | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [result, setResult] = useState<Schemas["RevisionSourcesResult"] | null>(null);

  const usable = sources.data?.items.filter((s) => s.latestRevision.extractStatus === "OK") ?? [];
  const selection = picked ?? new Set<string>();

  async function apply() {
    setBusy(true);
    setError(null);
    try {
      const res = await unwrap(
        api.PUT("/v1/revisions/{revision_id}/sources", {
          params: { path: { revision_id: rev.id } },
          body: { sourceRevisionIds: [...selection], version: rev.version },
        }),
      );
      setResult(res);
      setOpen(false);
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (result) {
    return (
      <Notice tone="success">
        Đã đổi nguồn: {result.matchedLinks} liên kết khớp bản mới, {result.unresolvedLinks} liên kết cần gán lại. Các khối
        liên quan chuyển sang &quot;Cần duyệt lại&quot;.
      </Notice>
    );
  }

  return (
    <div className="alert alert-warning stack">
      <div>
        Có bản nguồn mới hơn bản bài đang dùng. Bài không tự đổi.{" "}
        {!open ? (
          <button type="button" className="link-btn" onClick={() => setOpen(true)}>
            Chọn nguồn để đổi
          </button>
        ) : null}
      </div>
      {open ? (
        <>
          <ErrorBox error={error ?? sources.error} />
          {usable.map((s) => (
            <label key={s.id} className="check">
              <input
                type="checkbox"
                checked={selection.has(s.latestRevision.id)}
                onChange={() => {
                  const next = new Set(selection);
                  if (next.has(s.latestRevision.id)) next.delete(s.latestRevision.id);
                  else next.add(s.latestRevision.id);
                  setPicked(next);
                }}
              />
              {s.title} (bản mới nhất v{s.latestRevision.version})
              {rev.sourceRevisionIds.includes(s.latestRevision.id) ? <span className="muted small"> · đang dùng</span> : null}
            </label>
          ))}
          <p className="small">
            Khối có liên kết tới bản cũ, khối phụ thuộc và khối cha sẽ chuyển &quot;Cần duyệt lại&quot;. Liên kết không tìm
            thấy đoạn giống hệt ở bản mới sẽ cần gán lại.
          </p>
          <div className="row-actions">
            <Button variant="primary" busy={busy} disabled={selection.size === 0} onClick={() => void apply()}>
              Đổi nguồn
            </Button>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Hủy
            </Button>
          </div>
        </>
      ) : null}
    </div>
  );
}
