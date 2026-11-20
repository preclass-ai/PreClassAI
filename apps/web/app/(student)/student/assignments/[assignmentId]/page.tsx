"use client";

import { GuestSurveyCard } from "@/features/guest";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { use, useRef, useState, type FormEvent } from "react";
import { Button, DataNotice, ErrorBox, Loading, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { errorCode, errorMessage } from "@/lib/errors";
import { useAuth } from "@/lib/auth";
import { fmtDate, fmtNumber } from "@/lib/format";
import { SKILL } from "@/lib/labels";
import { newRequestId } from "@/lib/uuid";

type Item = Schemas["StudentItem"];
type ContentBlock = Schemas["StudentContentBlock"];

export default function StudentAssignmentPage({ params }: { params: Promise<{ assignmentId: string }> }) {
  const { assignmentId } = use(params);
  const { user } = useAuth();
  const key = ["student-assignment", assignmentId];
  const qc = useQueryClient();
  const [closed, setClosed] = useState(false);
  const a = useQuery({
    queryKey: key,
    queryFn: () =>
      unwrap(api.GET("/v1/student/assignments/{assignment_id}", { params: { path: { assignment_id: assignmentId } } })),
  });

  if (a.isPending) return <Loading />;
  if (!a.data) {
    const code = errorCode(a.error);
    return (
      <>
        <p className="crumbs">
          <Link href="/student">← Bài của em</Link>
        </p>
        {code === "WITHDRAWN" ? (
          <Notice tone="warning">Thầy cô đã thu hồi bài này để chỉnh sửa. Em sẽ được giao lại khi bài sẵn sàng.</Notice>
        ) : code === "NOT_FOUND" ? (
          <Notice>Bài chưa mở hoặc không có trong lớp của em.</Notice>
        ) : (
          <ErrorBox error={a.error} />
        )}
      </>
    );
  }

  const data = a.data;
  const isClosed = closed || new Date(data.dueAt).getTime() < Date.now();
  // Content and items share one position space in the snapshot: show them in authoring order.
  const entries = [
    ...data.blocks.filter((b) => b.kind !== "card_back").map((b) => ({ pos: b.position, block: b as ContentBlock })),
    ...data.items.map((i) => ({ pos: i.position, item: i as Item })),
  ].sort((x, y) => x.pos - y.pos);
  const answered = data.items.filter((i) => i.result).length;
  let n = 0;

  return (
    <article className="student">
      <p className="crumbs">
        <Link href="/student">← Bài của em</Link>
      </p>
      <header className="lesson-hero">
        <p className="eyebrow">BÀI KHÁM PHÁ ĐỊA LÍ</p>
        <h1>{data.title}</h1>
        <p>Quan sát, suy nghĩ và chọn câu trả lời của riêng em.</p>
        <div className="lesson-hero-meta">{user?.isGuest ? null : <span>◷ Hạn nộp {fmtDate(data.dueAt)}</span>}<strong>{answered}/{data.items.length} câu đã làm</strong></div>
        <div className="bar" aria-label={`Đã làm ${answered}/${data.items.length} câu`}><span style={{ width: `${data.items.length ? (100 * answered) / data.items.length : 0}%` }} /></div>
      </header>
      <DataNotice />
      {isClosed ? <Notice>Bài đã hết hạn nộp. Em vẫn xem lại được bài.</Notice> : null}
      {entries.map((e) =>
        "block" in e && e.block ? (
          <ContentView key={e.block.id} block={e.block} />
        ) : "item" in e && e.item ? (
          <ItemView
            key={e.item.id}
            no={++n}
            item={e.item}
            assignmentId={assignmentId}
            disabled={isClosed}
            onAnswered={() => void qc.invalidateQueries({ queryKey: key })}
            onClosed={() => setClosed(true)}
          />
        ) : null,
      )}
      <GuestSurveyCard />
    </article>
  );
}

function ContentView({ block }: { block: ContentBlock }) {
  const p = block.payload as Record<string, unknown>;
  const text = typeof p.text === "string" ? p.text : "";
  switch (block.kind) {
    case "heading":
      return <h2 className="student-section-title">{text}</h2>;
    case "instruction":
      return <p className="instruction student-content">{text}</p>;
    case "data_fact":
      return (
        <p className="fact student-content">
          <strong>{String(p.label ?? "")}</strong>: {fmtNumber(p.value as number)} {String(p.unit ?? "")}
          <span className="muted small">
            {" "}
            ({[p.region, p.period].filter(Boolean).join(", ")})
          </span>
        </p>
      );
    case "card_front":
      return <div className="card flashcard">{text}</div>;
    default:
      return <p className="student-content">{text}</p>;
  }
}

function ItemView({ no, item, assignmentId, disabled, onAnswered, onClosed }: {
  no: number;
  item: Item;
  assignmentId: string;
  disabled: boolean;
  onAnswered: () => void;
  onClosed: () => void;
}) {
  const [choice, setChoice] = useState<string>("");
  const [value, setValue] = useState("");
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [local, setLocal] = useState<Schemas["AttemptResult"] | null>(null);
  // Same requestId for retries of one answer: a resend after a network error returns the stored result.
  const requestId = useRef<string | null>(null);
  const result = item.result ?? local;

  async function submit(e: FormEvent) {
    e.preventDefault();
    let answer: Schemas["AnswerIn"];
    if (item.itemType === "MCQ") answer = { choice: choice as "A" | "B" | "C" | "D" };
    else if (item.itemType === "NUMERIC") answer = { value: Number(value.replace(",", ".")) };
    else answer = { text: text.trim() };
    requestId.current ??= newRequestId();
    setBusy(true);
    setError(null);
    try {
      const res = await unwrap(
        api.POST("/v1/student/assignments/{assignment_id}/attempts", {
          params: { path: { assignment_id: assignmentId } },
          body: { itemId: item.id, answer, requestId: requestId.current },
        }),
      );
      setLocal(res);
      onAnswered();
    } catch (err) {
      const code = errorCode(err);
      if (code === "ALREADY_ANSWERED") onAnswered();
      else if (code === "ASSIGNMENT_CLOSED") onClosed();
      if (code !== "NETWORK") requestId.current = null;
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const ready = item.itemType === "MCQ" ? !!choice : item.itemType === "NUMERIC" ? value.trim() !== "" && !Number.isNaN(Number(value.replace(",", "."))) : text.trim() !== "";

  return (
    <section className="card item" aria-labelledby={`q-${item.id}`}>
      <div className="item-top"><span className="question-number">Câu {no}</span><span className="muted small">{SKILL[item.skill]}</span></div>
      <p id={`q-${item.id}`} className="stem">
        {item.stem}
      </p>
      {result ? (
        <Result result={result} />
      ) : (
        <form className="stack" onSubmit={submit}>
          {item.itemType === "MCQ" ? (
            <div className="options" role="radiogroup">
              {item.options?.map((o) => (
                <label key={o.label} className={choice === o.label ? "option on" : "option"}>
                  <input
                    type="radio"
                    name={`q-${item.id}`}
                    value={o.label}
                    checked={choice === o.label}
                    disabled={disabled}
                    onChange={() => setChoice(o.label)}
                  />
                  <span>
                    <strong>{o.label}.</strong> {o.text}
                  </span>
                </label>
              ))}
            </div>
          ) : item.itemType === "NUMERIC" ? (
            <input
              inputMode="decimal"
              aria-label="Đáp số"
              placeholder="Nhập đáp số"
              value={value}
              disabled={disabled}
              onChange={(e) => setValue(e.target.value)}
            />
          ) : (
            <textarea
              rows={3}
              aria-label="Câu trả lời"
              value={text}
              disabled={disabled}
              onChange={(e) => setText(e.target.value)}
              maxLength={2000}
            />
          )}
          {error ? <div className="alert alert-danger" role="alert">{errorMessage(error)}</div> : null}
          <p className="muted small">Em chỉ nộp một lần. Lời giải xuất hiện sau khi nộp.</p>
          <Button type="submit" variant="primary" busy={busy} disabled={disabled || !ready}>
            Nộp câu trả lời
          </Button>
        </form>
      )}
    </section>
  );
}

function Result({ result }: { result: Schemas["AttemptResult"] }) {
  const tone = result.isCorrect === true ? "success" : result.isCorrect === false ? "danger" : "info";
  const label = result.isCorrect === true ? "Đúng" : result.isCorrect === false ? "Chưa đúng" : "Đã ghi nhận câu trả lời";
  return (
    <div className={`alert alert-${tone}`} role="status">
      <strong>{label}</strong>
      {result.explanation ? <p className="explanation">{result.explanation}</p> : null}
    </div>
  );
}
