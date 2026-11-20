"use client";

import { useQuery } from "@tanstack/react-query";
import { useState, type DragEvent, type FormEvent } from "react";
import { Button, ErrorBox, Field, Loading, Notice } from "@/components/ui";
import { api, postForm, unwrap, type Schemas } from "@/lib/api";
import { AnchorPreview } from "./anchors";

type Mode = "text" | "docx";
const MAX_BYTES = 10 * 1024 * 1024;
const ACCEPT = ".docx,.pdf,.xlsx,.pptx";

/** Text or DOCX input shared by "new source" and "new revision of a source". */
function ContentInput({ mode, setMode, text, setText, file, setFile, fileError, accept }: {
  mode: Mode;
  setMode: (m: Mode) => void;
  text: string;
  setText: (t: string) => void;
  file: File | null;
  setFile: (f: File | null) => void;
  fileError?: string | null;
  accept: "all" | "docx";
}) {
  return (
    <>
      <div className="segmented" role="radiogroup" aria-label="Kiểu nguồn">
        {(["text", "docx"] as const).map((m) => (
          <label key={m} className={mode === m ? "on" : undefined}>
            <input type="radio" name="mode" checked={mode === m} onChange={() => setMode(m)} />
            {m === "text" ? "Dán văn bản" : accept === "all" ? "Tải tệp (Word, PDF, Excel, PowerPoint)" : "Tải tệp DOCX"}
          </label>
        ))}
      </div>
      {mode === "text" ? (
        <Field label="Nội dung" hint="Mỗi đoạn, tiêu đề và ô bảng sẽ thành một đoạn nguồn (anchor) có mã riêng.">
          <textarea required rows={10} value={text} onChange={(e) => setText(e.target.value)} />
        </Field>
      ) : accept === "all" ? (
        <DropZone file={file} setFile={setFile} error={fileError ?? null} />
      ) : (
        <Field label="Tệp .docx" hint="Tối đa 10 MB, không có macro. Đọc đoạn văn, tiêu đề và bảng.">
          <input
            type="file"
            required
            accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </Field>
      )}
    </>
  );
}

const fmtSize = (b: number) => (b >= 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1).replace(".", ",")} MB` : `${Math.max(1, Math.round(b / 1024))} KB`);

/** Drag-and-drop or click-to-choose. The native file input stays focusable, so it works by keyboard too. */
function DropZone({ file, setFile, error }: { file: File | null; setFile: (f: File | null) => void; error: string | null }) {
  const [over, setOver] = useState(false);
  const take = (f: File | undefined) => setFile(f ?? null);
  const onDrop = (e: DragEvent) => {
    e.preventDefault();
    setOver(false);
    take(e.dataTransfer.files[0]);
  };
  return (
    <div className="field">
      <span className="field-label">Tệp giáo án</span>
      <label
        className={`dropzone${over ? " over" : ""}${error ? " bad" : ""}`}
        onDragOver={(e) => {
          e.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={onDrop}
      >
        <input type="file" required={!file} accept={ACCEPT} onChange={(e) => take(e.target.files?.[0])} />
        <strong>{file ? file.name : "Kéo tệp vào đây hoặc bấm để chọn"}</strong>
        <span className="muted small">
          {file ? fmtSize(file.size) : "Word (.docx), PDF, Excel (.xlsx), PowerPoint (.pptx) · tối đa 10 MB · không có macro"}
        </span>
      </label>
      {error ? <span className="field-hint" role="alert">{error}</span> : null}
    </div>
  );
}

/** After a file upload: what was read, warnings, and the anchors grouped by page / sheet / slide. */
function UploadResult({ source, fileName, onDone }: { source: Schemas["SourceOut"]; fileName: string; onDone: () => void }) {
  const rev = source.latestRevision;
  const anchors = useQuery({
    queryKey: ["anchors", rev.id],
    enabled: rev.extractStatus === "OK",
    queryFn: () => unwrap(api.GET("/v1/source-revisions/{source_revision_id}/anchors", { params: { path: { source_revision_id: rev.id } } })),
  });
  return (
    <div className="stack">
      {rev.extractStatus === "FAILED" ? (
        <Notice tone="warning">
          {rev.extractError === "SCANNED_PDF"
            ? "File là ảnh scan, vui lòng nạp bản có chữ (Word/PDF xuất từ Word)."
            : "Không đọc được nội dung của tệp này."}{" "}
          Nguồn đã được lưu nhưng chưa dùng để soạn bài được.
        </Notice>
      ) : (
        <Notice tone="success">
          Đã đọc {rev.anchorCount} đoạn nguồn từ “{fileName}”. Hãy xem lại bên dưới trước khi dùng để soạn bài.
        </Notice>
      )}
      {rev.extractStatus === "OK" ? (anchors.isPending ? <Loading /> : <AnchorPreview anchors={anchors.data?.items ?? []} />) : null}
      <div>
        <Button variant="primary" onClick={onDone}>
          Xong
        </Button>
      </div>
    </div>
  );
}

export function NewSourceForm({ onCreated, onSaved }: { onCreated: (s: Schemas["SourceOut"]) => void; onSaved?: () => void }) {
  const [mode, setMode] = useState<Mode>("text");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [visibility, setVisibility] = useState<"PRIVATE" | "SCHOOL">("PRIVATE");
  const [licenseNote, setLicenseNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [saved, setSaved] = useState<Schemas["SourceOut"] | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const license = licenseNote.trim() || null;
      let created: Schemas["SourceOut"];
      if (mode === "text") {
        created = await unwrap(
          api.POST("/v1/sources", { body: { title: title.trim(), text, visibility, licenseNote: license } }),
        );
      } else {
        if (!file) throw new Error("Hãy chọn tệp");
        const form = new FormData();
        form.set("file", file);
        form.set("title", title.trim());
        form.set("visibility", visibility);
        if (license) form.set("licenseNote", license);
        created = await postForm<Schemas["SourceOut"]>("/v1/sources/file", form);
        setSaved(created);
        onSaved?.();
        return;
      }
      onCreated(created);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const tooBig = mode === "docx" && file && file.size > MAX_BYTES ? "Tệp lớn hơn 10 MB." : null;
  if (saved && file) return <UploadResult source={saved} fileName={file.name} onDone={() => onCreated(saved)} />;

  return (
    <form className="stack" onSubmit={submit}>
      <ErrorBox error={error} />
      <Field label="Tên nguồn">
        <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
      </Field>
      <ContentInput mode={mode} setMode={setMode} text={text} setText={setText} file={file} setFile={setFile} fileError={tooBig} accept="all" />
      <div className="row">
        <Field label="Phạm vi">
          <select value={visibility} onChange={(e) => setVisibility(e.target.value as "PRIVATE" | "SCHOOL")}>
            <option value="PRIVATE">Riêng tôi</option>
            <option value="SCHOOL">Dùng chung trong trường</option>
          </select>
        </Field>
        <Field label={visibility === "SCHOOL" ? "Giấy phép / nguồn gốc (bắt buộc)" : "Giấy phép / nguồn gốc"}>
          <input
            required={visibility === "SCHOOL"}
            value={licenseNote}
            onChange={(e) => setLicenseNote(e.target.value)}
            placeholder="vd: SGK Địa lí 10, NXB Giáo dục"
          />
        </Field>
      </div>
      <div>
        <Button type="submit" variant="primary" busy={busy} disabled={!!tooBig}>
          Lưu nguồn
        </Button>
      </div>
    </form>
  );
}

export function NewRevisionForm({ sourceId, onCreated }: {
  sourceId: string;
  onCreated: (s: Schemas["SourceOut"]) => void;
}) {
  const [mode, setMode] = useState<Mode>("text");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      let updated: Schemas["SourceOut"];
      if (mode === "text") {
        updated = await unwrap(
          api.POST("/v1/sources/{source_id}/revisions", { params: { path: { source_id: sourceId } }, body: { text } }),
        );
      } else {
        if (!file) throw new Error("Hãy chọn tệp .docx");
        const form = new FormData();
        form.set("file", file);
        updated = await postForm<Schemas["SourceOut"]>(`/v1/sources/${sourceId}/revisions/docx`, form);
      }
      setText("");
      onCreated(updated);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <ErrorBox error={error} />
      <ContentInput mode={mode} setMode={setMode} text={text} setText={setText} file={file} setFile={setFile} accept="docx" />
      <p className="muted small">
        Bài đang soạn không tự đổi sang bản mới: bài sẽ hiện &quot;có bản nguồn mới&quot; để bạn chủ động đổi.
      </p>
      <div>
        <Button type="submit" variant="primary" busy={busy}>
          Tải bản mới
        </Button>
      </div>
    </form>
  );
}
