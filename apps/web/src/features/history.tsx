"use client";

import { useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { StateBadge } from "@/components/badges";
import { Button, Empty, ErrorBox, Loading } from "@/components/ui";
import { buildTree, summarize, type Block, type BlockNode } from "@/lib/blocks";
import { BlockCard } from "./block-view";
import { api, unwrap, type Schemas } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import { ACTOR, OPERATION } from "@/lib/labels";
import { keys, useBlocks, useRefreshLesson } from "./lesson-data";

/** Start a new DRAFT from the published revision (approvals are not carried over). */
export function NewRevisionButton({ lesson }: { lesson: Schemas["LessonOut"] }) {
  const refresh = useRefreshLesson(lesson.id);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function create() {
    if (!window.confirm("Tạo bản sửa mới? Bản đã xuất bản vẫn giữ nguyên cho học sinh; bản mới cần duyệt lại từ đầu.")) return;
    setBusy(true);
    setError(null);
    try {
      await unwrap(
        api.POST("/v1/revisions/{revision_id}/new-revision", {
          params: { path: { revision_id: lesson.currentRevision.id } },
        }),
      );
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <Button variant="primary" busy={busy} onClick={() => void create()}>
        Tạo bản sửa mới
      </Button>
      <ErrorBox error={error} />
    </>
  );
}

/** S06 Version History: revisions with diff summary, plus the lesson's event timeline. */
export function History({ lesson, canEdit }: { lesson: Schemas["LessonOut"]; canEdit: boolean }) {
  const [viewing, setViewing] = useState<string | null>(null);
  const history = useQuery({
    queryKey: keys.history(lesson.id),
    queryFn: () =>
      unwrap(api.GET("/v1/lessons/{lesson_id}/history", { params: { path: { lesson_id: lesson.id } } })),
  });

  if (history.isPending) return <Loading />;
  if (!history.data) return <ErrorBox error={history.error} />;
  const { revisions, events } = history.data;
  const sortedEvents = [...events].sort((a, b) => b.at.localeCompare(a.at));

  return (
    <div className="stack">
      <section className="card">
        <div className="section-head">
          <h2>Các bản</h2>
          {canEdit && lesson.currentRevision.state === "PUBLISHED" ? <NewRevisionButton lesson={lesson} /> : null}
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Bản</th>
                <th>Trạng thái</th>
                <th>Số khối</th>
                <th>Thay đổi so với bản trước</th>
                <th>Xuất bản lúc</th>
                <th><span className="sr-only">Xem</span></th>
              </tr>
            </thead>
            <tbody>
              {revisions.map((r) => (
                <Fragment key={r.revisionId}>
                <tr>
                  <td>#{r.revisionNo}</td>
                  <td>
                    <StateBadge state={r.state} />
                  </td>
                  <td>{r.blockCount}</td>
                  <td>
                    {r.diffSummary
                      ? `+${r.diffSummary.added ?? 0} thêm · ${r.diffSummary.changed ?? 0} sửa · −${r.diffSummary.removed ?? 0} xóa`
                      : "Chưa có"}
                  </td>
                  <td>{fmtDateTime(r.publishedAt)}</td>
                  <td>
                    <button
                      type="button"
                      className="link-btn small"
                      aria-expanded={viewing === r.revisionId}
                      onClick={() => setViewing(viewing === r.revisionId ? null : r.revisionId)}
                    >
                      {viewing === r.revisionId ? "Ẩn" : `Xem bản #${r.revisionNo}`}
                    </button>
                  </td>
                </tr>
                {viewing === r.revisionId ? (
                  <tr className="snapshot-row">
                    <td colSpan={6}>
                      <RevisionSnapshot revisionId={r.revisionId} />
                    </td>
                  </tr>
                ) : null}
                </Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <section className="card">
        <h2>Nhật ký</h2>
        {sortedEvents.length === 0 ? (
          <p className="muted">Chưa có sự kiện.</p>
        ) : (
          <ol className="timeline">
            {sortedEvents.map((e, i) => (
              <li key={`${e.at}-${i}`}>
                <span className="muted small">{fmtDateTime(e.at)}</span> <strong>{OPERATION[e.operation] ?? e.operation}</strong>{" "}
                <span className="muted">· {e.actorName ?? ACTOR[e.actorType] ?? e.actorType}</span>
                {e.summary ? <div className="small">{e.summary}</div> : null}
                {e.before && e.after && e.blockKind ? (
                  <div className="small edit-diff">
                    <div><span className="muted">Trước:</span> {summarize({ kind: e.blockKind as Block["kind"], payload: e.before })}</div>
                    <div><span className="muted">Sau:</span> {summarize({ kind: e.blockKind as Block["kind"], payload: e.after })}</div>
                  </div>
                ) : null}
              </li>
            ))}
          </ol>
        )}
      </section>
    </div>
  );
}

/** Read-only content of one revision (a published one is the immutable snapshot students received). */
function RevisionSnapshot({ revisionId }: { revisionId: string }) {
  const blocks = useBlocks(revisionId);
  if (blocks.isPending) return <Loading />;
  if (!blocks.data) return <ErrorBox error={blocks.error} />;
  const tree = buildTree(blocks.data.items);
  if (tree.length === 0) return <Empty>Bản này không có khối nào.</Empty>;
  return (
    <ol className="tree snapshot" aria-label="Nội dung của bản">
      {tree.map((n) => (
        <SnapshotNode key={n.block.id} node={n} />
      ))}
    </ol>
  );
}

function SnapshotNode({ node }: { node: BlockNode }) {
  return (
    <li>
      <BlockCard block={node.block} compact />
      {node.children.length > 0 ? (
        <ol className="tree">
          {node.children.map((c) => (
            <SnapshotNode key={c.block.id} node={c} />
          ))}
        </ol>
      ) : null}
    </li>
  );
}
