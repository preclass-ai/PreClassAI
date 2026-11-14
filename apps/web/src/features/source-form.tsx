"use client";

import { useState, type FormEvent } from "react";
import { Button, ErrorBox, Field } from "@/components/ui";
import { api, postForm, unwrap, type Schemas } from "@/lib/api";

type Mode = "text" | "docx";

/** Text or DOCX input shared by "new source" and "new revision of a source". */
function ContentInput({ mode, setMode, text, setText, setFile }: {
  mode: Mode;
  setMode: (m: Mode) => void;
  text: string;
  setText: (t: string) => void;
  setFile: (f: File | null) => void;
}) {
  return (
    <>
      <div className="segmented" role="radiogroup" aria-label="Kiểu nguồn">
        {(["text", "docx"] as const).map((m) => (
          <label key={m} className={mode === m ? "on" : undefined}>
            <input type="radio" name="mode" checked={mode === m} onChange={() => setMode(m)} />
            {m === "text" ? "Dán văn bản" : "Tải tệp DOCX"}
          </label>
        ))}
      </div>
      {mode === "text" ? (
        <Field label="Nội dung" hint="Mỗi đoạn, tiêu đề và ô bảng sẽ thành một đoạn nguồn (anchor) có mã riêng.">
          <textarea required rows={10} value={text} onChange={(e) => setText(e.target.value)} />
        </Field>
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

export function NewSourceForm({ onCreated }: { onCreated: (s: Schemas["SourceOut"]) => void }) {
  const [mode, setMode] = useState<Mode>("text");
  const [title, setTitle] = useState("");
  const [text, setText] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [visibility, setVisibility] = useState<"PRIVATE" | "SCHOOL">("PRIVATE");
  const [licenseNote, setLicenseNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

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
        if (!file) throw new Error("Hãy chọn tệp .docx");
        const form = new FormData();
        form.set("file", file);
        form.set("title", title.trim());
        form.set("visibility", visibility);
        if (license) form.set("licenseNote", license);
        created = await postForm<Schemas["SourceOut"]>("/v1/sources/docx", form);
      }
      onCreated(created);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <ErrorBox error={error} />
      <Field label="Tên nguồn">
        <input required maxLength={200} value={title} onChange={(e) => setTitle(e.target.value)} />
      </Field>
      <ContentInput mode={mode} setMode={setMode} text={text} setText={setText} setFile={setFile} />
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
        <Button type="submit" variant="primary" busy={busy}>
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
      <ContentInput mode={mode} setMode={setMode} text={text} setText={setText} setFile={setFile} />
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
