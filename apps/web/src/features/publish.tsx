"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useState, type FormEvent } from "react";
import { Badge, Button, ErrorBox, Field, Loading, Notice } from "@/components/ui";
import { api, ApiError, unwrap, type Schemas } from "@/lib/api";
import { isLocked, summarize } from "@/lib/blocks";
import { fmtDateTime, localInputToIso, toLocalInput } from "@/lib/format";
import { CHECK } from "@/lib/labels";
import { keys, useBlocks, useRefreshLesson } from "./lesson-data";

type Lesson = Schemas["LessonOut"];

/** S05 Publish Gate, then assignment to classes and withdrawal. */
export function PublishGate({ lesson }: { lesson: Lesson }) {
  const rev = lesson.currentRevision;
  const locked = isLocked(rev.state);
  return (
    <div className="stack">
      {!locked ? <GateCheck lesson={lesson} /> : <Notice tone="success">Bản #{rev.revisionNo} đã xuất bản.</Notice>}
      {lesson.publishedVersionId ? (
        <>
          <AssignPanel lesson={lesson} publishedId={lesson.publishedVersionId} />
          <WithdrawPanel lesson={lesson} publishedId={lesson.publishedVersionId} />
        </>
      ) : null}
    </div>
  );
}

function GateCheck({ lesson }: { lesson: Lesson }) {
  const rev = lesson.currentRevision;
  const refresh = useRefreshLesson(lesson.id);
  const check = useQuery({
    queryKey: keys.publishCheck(rev.id),
    queryFn: () =>
      unwrap(api.GET("/v1/revisions/{revision_id}/publish-check", { params: { path: { revision_id: rev.id } } })),
  });
  const blocks = useBlocks(rev.id);
  const byId = new Map((blocks.data?.items ?? []).map((b) => [b.id, b]));
  const [confirmed, setConfirmed] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [blockedIds, setBlockedIds] = useState<string[]>([]);

  async function publish(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setBlockedIds([]);
    try {
      await unwrap(
        api.POST("/v1/revisions/{revision_id}/publish", {
          params: { path: { revision_id: rev.id } },
          body: { confirmChecked: confirmed, version: rev.version },
        }),
      );
      setConfirmed(false);
      await refresh();
    } catch (err) {
      setError(err);
      if (err instanceof ApiError) setBlockedIds(err.blockIds);
      await refresh();
    } finally {
      setBusy(false);
    }
  }

  if (check.isPending) return <Loading />;
  if (!check.data) return <ErrorBox error={check.error} />;

  return (
    <form className="card stack" onSubmit={publish}>
      <h2>Kiểm tra trước khi xuất bản</h2>
      <ul className="checklist">
        {check.data.items.map((item) => (
          <li key={item.code} className={item.ok ? "ok" : "fail"}>
            <span aria-hidden="true">{item.ok ? "✓" : "✗"}</span>
            <div>
              <strong>{CHECK[item.code]}</strong>
              {!item.ok ? <div className="small">{item.message}</div> : null}
              {!item.ok && item.blockIds?.length ? <BlockLinks ids={item.blockIds} byId={byId} /> : null}
            </div>
          </li>
        ))}
      </ul>
      <ErrorBox error={error} />
      {blockedIds.length ? <BlockLinks ids={blockedIds} byId={byId} /> : null}
      <label className="check">
        <input type="checkbox" checked={confirmed} onChange={(e) => setConfirmed(e.target.checked)} />
        Tôi đã đọc từng khối cùng nguồn của nó và chịu trách nhiệm về nội dung xuất bản cho học sinh.
      </label>
      <p className="muted small">
        Sau khi xuất bản, bản này bị khóa (bất biến). Muốn sửa, tạo bản sửa mới; học sinh vẫn dùng bản đã giao.
      </p>
      <div>
        <Button type="submit" variant="primary" busy={busy} disabled={!check.data.canPublish || !confirmed}>
          Xuất bản
        </Button>
      </div>
    </form>
  );
}

function BlockLinks({ ids, byId }: { ids: string[]; byId: Map<string, Schemas["BlockOut"]> }) {
  return (
    <ul className="plain small">
      {ids.map((id) => {
        const b = byId.get(id);
        return (
          <li key={id}>
            <Link href={`?tab=editor&block=${id}`}>{b ? summarize(b) || "(khối trống)" : id}</Link>
          </li>
        );
      })}
    </ul>
  );
}

function AssignPanel({ lesson, publishedId }: { lesson: Lesson; publishedId: string }) {
  const classes = useQuery({ queryKey: ["classes"], queryFn: () => unwrap(api.GET("/v1/classes")) });
  const sameGrade = classes.data?.items.filter((c) => c.grade === lesson.grade) ?? [];
  const [classId, setClassId] = useState("");
  const [openAt, setOpenAt] = useState(() => toLocalInput(new Date()));
  const [dueAt, setDueAt] = useState(() => toLocalInput(new Date(Date.now() + 7 * 86_400_000)));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState<Schemas["AssignmentOut"] | null>(null);

  async function assign(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setDone(null);
    try {
      const a = await unwrap(
        api.POST("/v1/published/{published_id}/assignments", {
          params: { path: { published_id: publishedId } },
          body: { classId: classId || sameGrade[0]!.id, openAt: localInputToIso(openAt), dueAt: localInputToIso(dueAt) },
        }),
      );
      setDone(a);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card stack" onSubmit={assign}>
      <h2>Giao bài cho lớp</h2>
      <p className="muted small">Giao bản đã xuất bản mới nhất. Học sinh chỉ thấy bài từ thời điểm mở.</p>
      <ErrorBox error={error ?? classes.error} />
      {done ? (
        <Notice tone="success">
          Đã giao cho lớp {done.classCode}: mở {fmtDateTime(done.openAt)}, hạn {fmtDateTime(done.dueAt)}.{" "}
          <Link href={`/classes?class=${done.classId}`}>Xem tiến độ</Link>
        </Notice>
      ) : null}
      {classes.isPending ? (
        <Loading />
      ) : sameGrade.length === 0 ? (
        <p className="muted">Bạn chưa có lớp {lesson.grade} nào.</p>
      ) : (
        <>
          <div className="row">
            <Field label="Lớp">
              <select value={classId || sameGrade[0]!.id} onChange={(e) => setClassId(e.target.value)}>
                {sameGrade.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.code} ({c.studentCount} HS)
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Mở lúc">
              <input type="datetime-local" required value={openAt} onChange={(e) => setOpenAt(e.target.value)} />
            </Field>
            <Field label="Hạn nộp">
              <input type="datetime-local" required value={dueAt} onChange={(e) => setDueAt(e.target.value)} />
            </Field>
          </div>
          <div>
            <Button type="submit" variant="primary" busy={busy}>
              Giao bài
            </Button>
          </div>
        </>
      )}
    </form>
  );
}

function WithdrawPanel({ lesson, publishedId }: { lesson: Lesson; publishedId: string }) {
  const refresh = useRefreshLesson(lesson.id);
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [withdrawn, setWithdrawn] = useState<Schemas["PublishedOut"] | null>(null);

  async function withdraw(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const pv = await unwrap(
        api.POST("/v1/published/{published_id}/withdraw", {
          params: { path: { published_id: publishedId } },
          body: { reason: reason.trim() },
        }),
      );
      setWithdrawn(pv);
      setOpen(false);
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (withdrawn) {
    return <Notice tone="warning">Đã thu hồi bản xuất bản. Học sinh sẽ thấy thông báo bài đã bị thu hồi.</Notice>;
  }

  return (
    <section className="card stack">
      <div className="section-head">
        <h2>Thu hồi bản đã xuất bản</h2>
        {!open ? (
          <Button variant="danger" onClick={() => setOpen(true)}>
            Thu hồi…
          </Button>
        ) : (
          <Badge tone="danger">Không hoàn tác được</Badge>
        )}
      </div>
      <p className="muted small">Dùng khi phát hiện sai sót trong bài đã giao. Học sinh không mở được bài nữa.</p>
      {open ? (
        <form className="stack" onSubmit={withdraw}>
          <ErrorBox error={error} />
          <Field label="Lý do thu hồi">
            <textarea required rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
          <div className="row-actions">
            <Button type="submit" variant="danger" busy={busy}>
              Xác nhận thu hồi
            </Button>
            <Button variant="ghost" onClick={() => setOpen(false)}>
              Hủy
            </Button>
          </div>
        </form>
      ) : null}
    </section>
  );
}
