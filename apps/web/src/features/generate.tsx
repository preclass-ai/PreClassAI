"use client";

import { useQuery } from "@tanstack/react-query";
import { useEffect, useState, type FormEvent } from "react";
import { Badge, Button, ErrorBox, Field, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { SKILL } from "@/lib/labels";

type Skill = Schemas["WorksheetItemPayload"]["skill"];

/** The backend's deterministic stand-in (`mock-v1`) is not a real language model. */
export function isSimulated(model: string): boolean {
  return model.toLowerCase().startsWith("mock");
}

/** S02: start an async generation job and poll it until it finishes. AI output always needs teacher review. */
export function GeneratePanel({ lessonId, hasBlocks, onDone }: {
  lessonId: string;
  hasBlocks: boolean;
  onDone: () => void;
}) {
  const [outputType, setOutputType] = useState<"WORKSHEET" | "FLASHCARDS">("WORKSHEET");
  const [nItems, setNItems] = useState(5);
  const [skills, setSkills] = useState<Set<Skill>>(new Set(["READ_TABLE", "COMPARE"]));
  const [jobId, setJobId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const job = useQuery({
    queryKey: ["job", jobId],
    enabled: !!jobId,
    queryFn: () => unwrap(api.GET("/v1/jobs/{job_id}", { params: { path: { job_id: jobId! } } })),
    refetchInterval: (q) => (q.state.data && ["SUCCEEDED", "FAILED"].includes(q.state.data.status) ? false : 1500),
  });
  const status = job.data?.status;

  useEffect(() => {
    if (status === "SUCCEEDED") onDone();
  }, [status, onDone]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await unwrap(
        api.POST("/v1/lessons/{lesson_id}/generate", {
          params: { path: { lesson_id: lessonId } },
          body: { outputType, nItems, focusSkills: [...skills], mode: hasBlocks ? "append" : "initial" },
        }),
      );
      setJobId(res.jobId);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const running = !!jobId && (status === undefined || status === "QUEUED" || status === "RUNNING");

  return (
    <form className="card stack" onSubmit={submit}>
      <div className="section-head">
        <h2>{hasBlocks ? "Sinh thêm nội dung bằng AI" : "Sinh bản nháp bằng AI"}</h2>
        {job.data?.model && isSimulated(job.data.model) ? (
          <Badge tone="warning" title="Máy chủ đang dùng bộ sinh mô phỏng, chưa phải mô hình ngôn ngữ thật">
            AI mô phỏng
          </Badge>
        ) : null}
      </div>
      <p className="muted small">
        AI chỉ đọc các đoạn nguồn của bài. Mọi khối AI tạo đều cần bạn kiểm tra và duyệt; AI không tự duyệt.
      </p>
      <ErrorBox error={error} />
      <div className="row">
        <Field label="Loại học liệu">
          <select value={outputType} onChange={(e) => setOutputType(e.target.value as "WORKSHEET" | "FLASHCARDS")}>
            <option value="WORKSHEET">Phiếu học tập</option>
            <option value="FLASHCARDS">Thẻ ghi nhớ</option>
          </select>
        </Field>
        <Field label="Số câu / thẻ">
          <input type="number" min={1} max={20} value={nItems} onChange={(e) => setNItems(Number(e.target.value))} />
        </Field>
      </div>
      <fieldset className="chips">
        <legend className="field-label">Kỹ năng trọng tâm</legend>
        {(Object.keys(SKILL) as Skill[]).map((k) => (
          <label key={k} className="check">
            <input
              type="checkbox"
              checked={skills.has(k)}
              onChange={() =>
                setSkills((prev) => {
                  const next = new Set(prev);
                  if (next.has(k)) next.delete(k);
                  else next.add(k);
                  return next;
                })
              }
            />
            {SKILL[k]}
          </label>
        ))}
      </fieldset>
      {running ? <Notice>Đang sinh nội dung… ({status === "RUNNING" ? "đang chạy" : "đang chờ"})</Notice> : null}
      {status === "SUCCEEDED" ? (
        <Notice tone="success">
          Đã sinh {job.data?.blockCount ?? 0} khối{job.data?.model ? ` (mô hình: ${job.data.model})` : ""}. Hãy kiểm tra từng
          khối.
        </Notice>
      ) : null}
      {status === "FAILED" ? (
        <Notice tone="danger">Sinh nội dung thất bại{job.data?.error ? `: ${job.data.error}` : ""}. Bạn có thể thử lại.</Notice>
      ) : null}
      <div>
        <Button type="submit" variant="primary" busy={busy} disabled={running}>
          {hasBlocks ? "Sinh thêm" : "Sinh bản nháp"}
        </Button>
      </div>
    </form>
  );
}
