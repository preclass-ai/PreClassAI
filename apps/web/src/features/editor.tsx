"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button, Empty, ErrorBox, Field, Loading, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { buildTree, childKinds, emptyPayload, isLocked, type Block, type BlockNode, type BlockPayload } from "@/lib/blocks";
import { useDraft } from "@/lib/draft";
import { errorCode } from "@/lib/errors";
import { KIND } from "@/lib/labels";
import { BlockCard } from "./block-view";
import { GeneratePanel } from "./generate";
import { SourceInspector } from "./inspector";
import { useBlocks, useRefreshLesson } from "./lesson-data";
import { cleanPayload, PayloadEditor } from "./payload-editor";
import { ReplaceSourcesPanel } from "./replace-sources";
import { NewRevisionButton } from "./history";
import { ReviewActions } from "./review";

type Lesson = Schemas["LessonOut"];

/** S03 Content Editor + Source Inspector. */
export function Editor({ lesson, canEdit }: { lesson: Lesson; canEdit: boolean }) {
  const rev = lesson.currentRevision;
  const blocks = useBlocks(rev.id);
  const refresh = useRefreshLesson(lesson.id);
  const router = useRouter();
  const params = useSearchParams();
  const selected = params.get("block");
  const [adding, setAdding] = useState<{ parent: Block | null } | null>(null);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const locked = isLocked(rev.state);
  const editable = canEdit && !locked;

  function select(id: string | null) {
    const q = new URLSearchParams(params.toString());
    if (id) q.set("block", id);
    else q.delete("block");
    router.replace(`?${q.toString()}`, { scroll: false });
  }

  async function validate() {
    setValidating(true);
    setError(null);
    try {
      await unwrap(api.POST("/v1/revisions/{revision_id}/validate", { params: { path: { revision_id: rev.id } } }));
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setValidating(false);
    }
  }

  const items = blocks.data?.items ?? [];
  const tree = buildTree(items);
  const current = items.find((b) => b.id === selected) ?? null;

  return (
    <div className="stack">
      {locked ? (
        <Notice tone="info">
          Bản #{rev.revisionNo} đã xuất bản nên không sửa được.{" "}
          {canEdit && rev.state === "PUBLISHED" ? <NewRevisionButton lesson={lesson} /> : null}
        </Notice>
      ) : null}
      {editable && rev.newerSourceAvailable ? <ReplaceSourcesPanel lesson={lesson} /> : null}
      {editable && !blocks.isPending ? (
        <GeneratePanel lessonId={lesson.id} hasBlocks={items.length > 0} onDone={refresh} />
      ) : null}
      <ErrorBox error={error ?? blocks.error} />
      <div className="editor">
        <section className="editor-list" aria-label="Các khối nội dung">
          <div className="section-head">
            <h2>Nội dung ({items.length} khối)</h2>
            <div className="row-actions">
              {editable ? (
                <>
                  <Button variant="ghost" busy={validating} onClick={() => void validate()}>
                    Kiểm tra lại
                  </Button>
                  <Button onClick={() => setAdding({ parent: null })}>Thêm khối</Button>
                </>
              ) : null}
            </div>
          </div>
          {adding && adding.parent === null ? (
            <NewBlockForm revisionId={rev.id} parent={null} onDone={() => setAdding(null)} onCreated={refresh} />
          ) : null}
          {blocks.isPending ? (
            <Loading />
          ) : tree.length === 0 ? (
            <Empty>Bản này chưa có nội dung. Sinh bản nháp bằng AI hoặc thêm khối thủ công.</Empty>
          ) : (
            <ol className="tree">
              {tree.map((node) => (
                <TreeItem
                  key={node.block.id}
                  node={node}
                  selected={selected}
                  onSelect={select}
                  editable={editable}
                  adding={adding}
                  setAdding={setAdding}
                  revisionId={rev.id}
                  onCreated={refresh}
                />
              ))}
            </ol>
          )}
        </section>
        <aside className={current ? "editor-inspector open" : "editor-inspector"} aria-label="Chi tiết khối">
          {current ? (
            <BlockDetail
              key={current.id + current.version}
              block={current}
              lesson={lesson}
              editable={editable}
              canReview={!locked}
              onClose={() => select(null)}
              onChanged={refresh}
            />
          ) : (
            <p className="muted">Chọn một khối để xem nguồn, kết quả kiểm tra và lịch sử.</p>
          )}
        </aside>
      </div>
    </div>
  );
}

function TreeItem(props: {
  node: BlockNode;
  selected: string | null;
  onSelect: (id: string) => void;
  editable: boolean;
  adding: { parent: Block | null } | null;
  setAdding: (a: { parent: Block | null } | null) => void;
  revisionId: string;
  onCreated: () => Promise<unknown>;
}) {
  const { node, selected, onSelect, editable, adding, setAdding, revisionId, onCreated } = props;
  const b = node.block;
  const kinds = childKinds(b.kind);
  return (
    <li>
      <button
        type="button"
        className={b.id === selected ? "tree-node selected" : "tree-node"}
        aria-pressed={b.id === selected}
        onClick={() => onSelect(b.id)}
      >
        <BlockCard block={b} compact />
      </button>
      {editable && kinds.length > 0 ? (
        <button type="button" className="link-btn small add-child" onClick={() => setAdding({ parent: b })}>
          + thêm {kinds.map((k) => KIND[k].toLowerCase()).join(" / ")}
        </button>
      ) : null}
      {adding?.parent?.id === b.id ? (
        <NewBlockForm revisionId={revisionId} parent={b} onDone={() => setAdding(null)} onCreated={onCreated} />
      ) : null}
      {node.children.length > 0 ? (
        <ol className="tree">
          {node.children.map((c) => (
            <TreeItem key={c.block.id} {...props} node={c} />
          ))}
        </ol>
      ) : null}
    </li>
  );
}

function BlockDetail({ block, lesson, editable, canReview, onClose, onChanged }: {
  block: Block;
  lesson: Lesson;
  editable: boolean;
  canReview: boolean;
  onClose: () => void;
  onChanged: () => Promise<unknown>;
}) {
  // Autosaved per block AND version: a draft never resurfaces over content that changed since.
  const draft = useDraft<BlockPayload>(`block:${block.id}:v${block.version}`, block.payload);
  const payload = draft.value;
  const setPayload = draft.setValue;
  const [editing, setEditing] = useState(editable && draft.restored);
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => heading.current?.focus(), []);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function save(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await unwrap(
        api.PATCH("/v1/blocks/{block_id}", {
          params: { path: { block_id: block.id } },
          body: { payload: cleanPayload(block.kind, payload), version: block.version },
        }),
      );
      draft.discard(block.payload);
      setEditing(false);
      await onChanged();
    } catch (err) {
      setError(err);
      // Keep the local draft on conflict: the teacher can copy it over the newer version.
      if (errorCode(err) === "VERSION_CONFLICT") await onChanged();
    } finally {
      setBusy(false);
    }
  }

  async function remove() {
    if (!window.confirm("Xóa khối này (và các khối con)? Các khối phụ thuộc đã duyệt sẽ cần duyệt lại.")) return;
    setBusy(true);
    setError(null);
    try {
      await unwrap(api.DELETE("/v1/blocks/{block_id}", { params: { path: { block_id: block.id } } }));
      onClose();
      await onChanged();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div
      className="stack"
      onKeyDown={(e) => {
        if (e.key === "Escape" && !editing) onClose();
      }}
    >
      <div className="section-head">
        <h2 ref={heading} tabIndex={-1}>{KIND[block.kind]}</h2>
        <Button variant="ghost" onClick={onClose} aria-label="Đóng">
          ✕
        </Button>
      </div>
      <ErrorBox error={error} />
      {editing && draft.restored ? (
        <Notice tone="info">Đã khôi phục nội dung thầy cô đang sửa dở (chưa lưu lên máy chủ).</Notice>
      ) : null}
      {editing ? (
        <form className="stack" onSubmit={save}>
          <PayloadEditor kind={block.kind} value={payload} onChange={setPayload} />
          {block.reviewStatus === "APPROVED" ? (
            <Notice tone="warning">Khối đã duyệt: sau khi sửa, khối này và các khối phụ thuộc sẽ cần duyệt lại.</Notice>
          ) : null}
          <div className="row-actions">
            <Button type="submit" variant="primary" busy={busy}>
              Lưu
            </Button>
            <Button
              variant="ghost"
              onClick={() => {
                setEditing(false);
                draft.discard(block.payload);
              }}
            >
              Hủy
            </Button>
          </div>
        </form>
      ) : (
        <>
          <BlockCard block={block} />
          {editable ? (
            <div className="row-actions">
              <Button onClick={() => setEditing(true)}>Sửa nội dung</Button>
              <Button variant="danger" busy={busy} onClick={() => void remove()}>
                Xóa
              </Button>
            </div>
          ) : null}
          {canReview ? <ReviewActions block={block} lessonId={lesson.id} /> : null}
        </>
      )}
      <SourceInspector
        blockId={block.id}
        sourceRevisionIds={lesson.currentRevision.sourceRevisionIds}
        canEdit={editable}
        onChanged={() => void onChanged()}
      />
    </div>
  );
}

function NewBlockForm({ revisionId, parent, onDone, onCreated }: {
  revisionId: string;
  parent: Block | null;
  onDone: () => void;
  onCreated: () => Promise<unknown>;
}) {
  const kinds = childKinds(parent?.kind ?? null);
  const [kind, setKind] = useState<Block["kind"]>(kinds[0] ?? "paragraph");
  const [payload, setPayload] = useState<BlockPayload>(emptyPayload(kind));
  const [isFactual, setIsFactual] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await unwrap(
        api.POST("/v1/revisions/{revision_id}/blocks", {
          params: { path: { revision_id: revisionId } },
          body: { kind, payload: cleanPayload(kind, payload), parentId: parent?.id ?? null, isFactual },
        }),
      );
      onDone();
      await onCreated();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="card stack inset" onSubmit={submit}>
      <ErrorBox error={error} />
      <Field label="Loại khối">
        <select
          value={kind}
          onChange={(e) => {
            const k = e.target.value as Block["kind"];
            setKind(k);
            setPayload(emptyPayload(k));
          }}
        >
          {kinds.map((k) => (
            <option key={k} value={k}>
              {KIND[k]}
            </option>
          ))}
        </select>
      </Field>
      <PayloadEditor kind={kind} value={payload} onChange={setPayload} />
      <label className="check">
        <input type="checkbox" checked={isFactual} onChange={(e) => setIsFactual(e.target.checked)} />
        Khối nêu sự kiện / số liệu (cần nguồn)
      </label>
      <div className="row-actions">
        <Button type="submit" variant="primary" busy={busy}>
          Thêm
        </Button>
        <Button variant="ghost" onClick={onDone}>
          Hủy
        </Button>
      </div>
    </form>
  );
}
