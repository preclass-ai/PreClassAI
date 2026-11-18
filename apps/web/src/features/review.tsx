"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Button, Empty, ErrorBox, Field, Loading, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { isLocked, summarize, type Block } from "@/lib/blocks";
import { errorCode } from "@/lib/errors";
import { KIND, REVIEW_STATUS, type ReviewStatus } from "@/lib/labels";
import { BlockCard } from "./block-view";
import { EvidenceList, ValidationList } from "./inspector";
import { invalidateLesson, keys, useBlocks, useProvenance, useRefreshLesson } from "./lesson-data";

const FILTERS: ReviewStatus[] = ["FLAGGED", "REVIEW_AGAIN", "UNREVIEWED", "AUTO_CHECKED", "APPROVED", "REJECTED"];
const DEFAULT: ReviewStatus[] = ["FLAGGED", "REVIEW_AGAIN", "UNREVIEWED", "AUTO_CHECKED"];

/** S04 Review Queue: one block at a time, evidence first, hash-bound decisions, no "approve all". */
export function ReviewQueue({ lesson }: { lesson: Schemas["LessonOut"] }) {
  const rev = lesson.currentRevision;
  const [statuses, setStatuses] = useState<Set<ReviewStatus>>(new Set(DEFAULT));
  const queue = useQuery({
    queryKey: [...keys.reviewQueue(rev.id), [...statuses].sort().join(",")],
    enabled: statuses.size > 0,
    queryFn: () =>
      unwrap(
        api.GET("/v1/revisions/{revision_id}/review-queue", {
          params: { path: { revision_id: rev.id }, query: { status: [...statuses] } },
        }),
      ),
  });
  const all = useBlocks(rev.id);
  const byId = new Map((all.data?.items ?? []).map((b) => [b.id, b]));
  const locked = isLocked(rev.state);

  return (
    <div className="stack">
      {locked ? <Notice>Bản này đã xuất bản: chỉ xem, không duyệt thêm.</Notice> : null}
      <fieldset className="chips">
        <legend className="field-label">Hiện khối</legend>
        {FILTERS.map((s) => (
          <label key={s} className="check">
            <input
              type="checkbox"
              checked={statuses.has(s)}
              onChange={() =>
                setStatuses((prev) => {
                  const next = new Set(prev);
                  if (next.has(s)) next.delete(s);
                  else next.add(s);
                  return next;
                })
              }
            />
            {REVIEW_STATUS[s].label}
          </label>
        ))}
      </fieldset>
      <ErrorBox error={queue.error} />
      {queue.isFetching && !queue.data ? (
        <Loading />
      ) : (queue.data?.items.length ?? 0) === 0 ? (
        <Empty>Không còn khối nào trong danh sách này.</Empty>
      ) : (
        <ol className="review-list">
          {queue.data?.items.map((b) => (
            <li key={b.id}>
              <ReviewCard
                block={b}
                parent={b.parentId ? byId.get(b.parentId) : undefined}
                lessonId={lesson.id}
                readOnly={locked}
              />
            </li>
          ))}
        </ol>
      )}
    </div>
  );
}

function ReviewCard({ block, parent, lessonId, readOnly }: {
  block: Block;
  parent: Block | undefined;
  lessonId: string;
  readOnly: boolean;
}) {
  const prov = useProvenance(block.id);

  return (
    <article className="card review-card">
      {parent ? (
        <p className="muted small">
          Thuộc {KIND[parent.kind].toLowerCase()}: {summarize(parent)}
        </p>
      ) : null}
      <div className="review-grid">
        <div className="stack">
          <h3>Bằng chứng từ nguồn</h3>
          {prov.isPending ? <Loading /> : prov.data ? <EvidenceList links={prov.data.links} /> : <ErrorBox error={prov.error} />}
          {block.noSourceReason ? <p className="no-source">Lý do không có nguồn: {block.noSourceReason}</p> : null}
        </div>
        <div className="stack">
          <h3>Nội dung cần duyệt</h3>
          <BlockCard block={block} />
          {prov.data ? <ValidationList results={prov.data.validations} /> : null}
        </div>
      </div>
      {!readOnly ? <ReviewActions block={block} lessonId={lessonId} /> : null}
    </article>
  );
}

/**
 * Approve / request changes / reject ONE block, bound to the contentHash on screen (STALE_REVIEW if it changed).
 * Used in the review queue (S04) and next to the selected block in the editor (S03). There is no "approve all".
 */
export function ReviewActions({ block, lessonId }: { block: Block; lessonId: string }) {
  const refresh = useRefreshLesson(lessonId);
  const qc = useQueryClient();
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState<Schemas["ReviewRequest"]["action"] | null>(null);
  const [error, setError] = useState<unknown>(null);
  const blockers = block.blockerCount ?? 0;

  async function decide(action: Schemas["ReviewRequest"]["action"]) {
    setBusy(action);
    setError(null);
    try {
      await unwrap(
        api.POST("/v1/blocks/{block_id}/reviews", {
          params: { path: { block_id: block.id } },
          body: { action, contentHash: block.contentHash, note: note.trim() || null },
        }),
      );
      setNote("");
      await invalidateLesson(qc, lessonId, block.id);
    } catch (err) {
      setError(err);
      if (errorCode(err) === "STALE_REVIEW") await refresh();
      else void qc.invalidateQueries({ queryKey: keys.provenance(block.id) });
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="stack review-actions">
      <ErrorBox error={error} />
      {blockers > 0 ? (
        <Notice tone="danger">Còn {blockers} lỗi chặn: sửa nội dung hoặc nguồn trước khi duyệt.</Notice>
      ) : null}
      <Field label="Ghi chú (không bắt buộc)">
        <input value={note} onChange={(e) => setNote(e.target.value)} maxLength={1000} />
      </Field>
      <div className="row-actions">
        <Button
          variant="primary"
          busy={busy === "APPROVE"}
          disabled={!!busy || blockers > 0}
          title={blockers > 0 ? "Còn lỗi chặn: sửa khối trước khi duyệt" : undefined}
          onClick={() => void decide("APPROVE")}
        >
          Duyệt khối này
        </Button>
        <Button busy={busy === "REQUEST_CHANGES"} disabled={!!busy} onClick={() => void decide("REQUEST_CHANGES")}>
          Yêu cầu sửa
        </Button>
        <Button variant="danger" busy={busy === "REJECT"} disabled={!!busy} onClick={() => void decide("REJECT")}>
          Từ chối
        </Button>
      </div>
    </div>
  );
}
