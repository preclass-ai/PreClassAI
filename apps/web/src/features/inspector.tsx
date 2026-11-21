"use client";

import { useState, type FormEvent } from "react";
import { Badge, Button, ErrorBox, Field, Loading } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { errorCode } from "@/lib/errors";
import { fmtDateTime } from "@/lib/format";
import { ACTOR, OPERATION, RELATION } from "@/lib/labels";
import { anchorKind, locatorText } from "./anchors";
import { useLessonAnchors, useProvenance } from "./lesson-data";

type Relation = Schemas["LinkIn"]["relation"];

const REVIEW_ACTION: Record<Schemas["ReviewEventOut"]["action"], string> = {
  APPROVE: "Duyệt",
  REJECT: "Từ chối",
  REQUEST_CHANGES: "Yêu cầu sửa",
};

/** Evidence shown first: the exact source excerpts behind a block. */
export function EvidenceList({ links }: { links: Schemas["ProvenanceLinkOut"][] }) {
  if (links.length === 0) return <p className="muted small">Khối này không liên kết đoạn nguồn nào.</p>;
  return (
    <ul className="evidence">
      {links.map((l) => (
        <li key={l.id} className={l.status === "UNRESOLVED" ? "unresolved" : undefined}>
          <div className="evidence-head">
            <span className="mono">{l.anchor.code}</span>
            <span>{RELATION[l.relation]}</span>
            {l.status === "UNRESOLVED" ? <Badge tone="danger">Nguồn đã đổi, cần gán lại</Badge> : null}
          </div>
          <blockquote>{l.anchor.excerpt}</blockquote>
          <div className="muted small">
            {l.anchor.sourceTitle} (v{l.anchor.sourceVersion}) · {anchorKind(l.anchor.kind)} {locatorText(l.anchor.locator)}
          </div>
          {l.rationale ? <div className="small">Lý giải: {l.rationale}</div> : null}
        </li>
      ))}
    </ul>
  );
}

export function ValidationList({ results }: { results: Schemas["ValidationResultOut"][] }) {
  const current = results.filter((r) => r.isCurrent);
  if (current.length === 0) return <p className="muted small">Chưa có kết quả kiểm tra cho nội dung hiện tại.</p>;
  return (
    <ul className="plain">
      {current.map((r) => (
        <li key={r.id}>
          <Badge tone={r.outcome === "PASS" ? "success" : r.severity === "BLOCKER" ? "danger" : "warning"}>
            {r.rule} {r.outcome === "PASS" ? "đạt" : r.severity === "BLOCKER" ? "lỗi chặn" : "cảnh báo"}
          </Badge>{" "}
          {r.method !== "rule" ? <span className="muted small">{r.method}</span> : null}
          {r.outcome === "FAIL" && r.evidence && Object.keys(r.evidence).length ? (
            <pre className="evidence-json">{JSON.stringify(r.evidence, null, 1)}</pre>
          ) : null}
        </li>
      ))}
    </ul>
  );
}

/** S03 Source Inspector: links + excerpts, validation, transformation history, reviews of one block. */
export function SourceInspector({ blockId, sourceRevisionIds, canEdit, onChanged }: {
  blockId: string;
  sourceRevisionIds: string[];
  canEdit: boolean;
  onChanged: () => void;
}) {
  const prov = useProvenance(blockId);
  const [editing, setEditing] = useState(false);

  if (prov.isPending) return <Loading />;
  if (!prov.data) return <ErrorBox error={prov.error} />;
  const { block, links, validations, events, reviews } = prov.data;

  return (
    <div className="stack">
      <section>
        <div className="section-head">
          <h3>Nguồn</h3>
          {canEdit && !editing ? (
            <Button variant="ghost" onClick={() => setEditing(true)}>
              Sửa liên kết nguồn
            </Button>
          ) : null}
        </div>
        {editing ? (
          <ProvenanceEditor
            block={block}
            current={links}
            sourceRevisionIds={sourceRevisionIds}
            onCancel={() => setEditing(false)}
            onSaved={() => {
              setEditing(false);
              onChanged();
            }}
          />
        ) : (
          <>
            <EvidenceList links={links} />
            {block.noSourceReason ? <p className="no-source">Lý do không có nguồn: {block.noSourceReason}</p> : null}
          </>
        )}
      </section>
      <section>
        <h3>Kiểm tra tự động</h3>
        <ValidationList results={validations} />
      </section>
      <section>
        <h3>Lịch sử biến đổi</h3>
        <ul className="plain small">
          {events.map((e) => (
            <li key={e.id}>
              {fmtDateTime(e.createdAt)} · {OPERATION[e.operation] ?? e.operation} · {ACTOR[e.actorType]}
              {e.generatorVersion ? (
                <span className="muted">
                  {" "}
                  ({e.generatorVersion}
                  {e.generatorVersion.toLowerCase().startsWith("mock") ? ", mô phỏng" : ""})
                </span>
              ) : null}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h3>Các lần duyệt</h3>
        {reviews.length === 0 ? (
          <p className="muted small">Chưa có.</p>
        ) : (
          <ul className="plain small">
            {reviews.map((r) => (
              <li key={r.id}>
                {fmtDateTime(r.createdAt)} · {r.reviewerName}: {REVIEW_ACTION[r.action]}
                {!r.isValid ? <Badge tone="warning">không còn hiệu lực</Badge> : null}
                {r.note ? <div className="muted">“{r.note}”</div> : null}
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  );
}

function ProvenanceEditor({ block, current, sourceRevisionIds, onCancel, onSaved }: {
  block: Schemas["BlockOut"];
  current: Schemas["ProvenanceLinkOut"][];
  sourceRevisionIds: string[];
  onCancel: () => void;
  onSaved: () => void;
}) {
  const anchors = useLessonAnchors(sourceRevisionIds);
  const [picked, setPicked] = useState<Map<string, Relation>>(
    () => new Map(current.filter((l) => l.status === "VERIFIED").map((l) => [l.anchor.anchorId, l.relation])),
  );
  const [noSource, setNoSource] = useState(current.length === 0 && !!block.noSourceReason);
  const [reason, setReason] = useState(block.noSourceReason ?? "");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body = noSource
        ? { noSourceReason: reason.trim(), version: block.version }
        : {
            links: [...picked].map(([anchorId, relation]) => ({ anchorId, relation })),
            version: block.version,
          };
      await unwrap(api.PUT("/v1/blocks/{block_id}/provenance", { params: { path: { block_id: block.id } }, body }));
      onSaved();
    } catch (err) {
      setError(err);
      if (errorCode(err) === "VERSION_CONFLICT") onSaved();
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={save}>
      <ErrorBox error={error} />
      <label className="check">
        <input type="checkbox" checked={noSource} onChange={(e) => setNoSource(e.target.checked)} />
        Khối này không có nguồn (ghi lý do)
      </label>
      {noSource ? (
        <Field label="Lý do không có nguồn">
          <textarea required rows={2} value={reason} onChange={(e) => setReason(e.target.value)} />
        </Field>
      ) : anchors.isPending ? (
        <Loading />
      ) : (
        <div className="anchor-picker">
          <ErrorBox error={anchors.error} />
          {anchors.data?.map((group) =>
            group.anchors.map((a) => {
              const rel = picked.get(a.id);
              return (
                <div key={a.id} className={rel ? "anchor-row on" : "anchor-row"}>
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={!!rel}
                      onChange={() =>
                        setPicked((prev) => {
                          const next = new Map(prev);
                          if (next.has(a.id)) next.delete(a.id);
                          else next.set(a.id, "derived_from");
                          return next;
                        })
                      }
                    />
                    <span>
                      <span className="mono">{a.code}</span> {a.excerpt}
                    </span>
                  </label>
                  {rel ? (
                    <select
                      aria-label="Quan hệ"
                      value={rel}
                      onChange={(e) => setPicked((prev) => new Map(prev).set(a.id, e.target.value as Relation))}
                    >
                      {Object.entries(RELATION).map(([k, v]) => (
                        <option key={k} value={k}>
                          {v}
                        </option>
                      ))}
                    </select>
                  ) : null}
                </div>
              );
            }),
          )}
        </div>
      )}
      <div className="row-actions">
        <Button type="submit" variant="primary" busy={busy} disabled={!noSource && picked.size === 0}>
          Lưu nguồn
        </Button>
        <Button variant="ghost" onClick={onCancel}>
          Hủy
        </Button>
      </div>
    </form>
  );
}
