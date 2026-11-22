"use client";

import { GuestBanner, GuestSurveyCard } from "@/features/guest";
import { HabitBar, HabitItem } from "@/features/habit";
import { ReviewAsk, ReviewStepper, Steps, type Stage } from "@/features/review-step";
import { habitKey } from "@/features/habit-api";
import { FocusTimer, PersonalizationBar, usePersonalizationOn, usePrefs } from "@/features/personalization";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { use, useRef, useState, type FormEvent } from "react";
import { Button, ErrorBox, Loading, Notice } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { errorCode, errorMessage } from "@/lib/errors";
import { fmtDate, fmtNumber, parseAnswerNumber } from "@/lib/format";
import { SKILL } from "@/lib/labels";
import { newRequestId } from "@/lib/uuid";

type Item = Schemas["StudentItem"];
type ContentBlock = Schemas["StudentContentBlock"];

export default function StudentAssignmentPage({ params }: { params: Promise<{ assignmentId: string }> }) {
  const { assignmentId } = use(params);
  const key = ["student-assignment", assignmentId];
  const qc = useQueryClient();
  const [closed, setClosed] = useState(false);
  const [focus, setFocus] = useState(false);
  const [idx, setIdx] = useState(0);
  const [view, setView] = useState<Stage | "auto">("auto"); // the student's own choice; "auto" follows what the server remembers
  const [cardId, setCardId] = useState<string | null>(null);
  const persOn = usePersonalizationOn();
  const prefs = usePrefs(persOn);
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
  const review = data.review ?? [];
  const hasReview = review.length > 0; // no approved review cards: the lesson is the quiz alone, as before
  const rs = { seenIds: [], checks: {}, reviewed: false, choice: null, ...data.reviewState };
  const auto: Stage = !hasReview ? "quiz" : rs.choice === null ? "ask" : rs.choice === "not_yet" && !rs.reviewed ? "review" : "quiz";
  const stage: Stage = !hasReview ? "quiz" : view === "auto" ? auto : view;
  const reload = () => void qc.invalidateQueries({ queryKey: key });
  const openReview = (id: string) => {
    setCardId(id);
    setView("review");
    window.scrollTo({ top: 0 });
  };
  const isClosed = closed || new Date(data.dueAt).getTime() < Date.now();
  // Content and items share one position space in the snapshot: show them in authoring order.
  const entries = [
    ...data.blocks.filter((b) => b.kind !== "card_back").map((b) => ({ pos: b.position, block: b as ContentBlock })),
    ...data.items.map((i) => ({ pos: i.position, item: i as Item })),
  ].sort((x, y) => x.pos - y.pos);
  const answered = data.items.filter((i) => i.result).length;
  let n = 0;
  const items = data.items.slice().sort((x, y) => x.position - y.position);
  const inFocus = focus && persOn && items.length > 0 && stage === "quiz";
  const cur = items[Math.min(idx, items.length - 1)];
  const content = entries.filter((e): e is { pos: number; block: ContentBlock } => "block" in e);
  const itemProps = (item: Item, no: number) => ({
    no,
    item,
    assignmentId,
    disabled: isClosed,
    onAnswered: () => {
      void qc.invalidateQueries({ queryKey: key });
      void qc.invalidateQueries({ queryKey: habitKey(assignmentId) }); // streak + daily goal
    },
    onClosed: () => setClosed(true),
    onOpenReview: hasReview ? openReview : undefined,
  });

  return (
    <article className="student">
      {inFocus ? null : (
        <p className="crumbs">
          <Link href="/student">← Bài của em</Link>
        </p>
      )}
      {inFocus ? null : (
        <header className="lesson-hero">
          <p className="eyebrow">Bài tập</p>
          <h1>{data.title}</h1>
          <p>Quan sát, suy nghĩ và chọn câu trả lời của riêng em.</p>
          <div className="lesson-hero-meta"><span>◷ Hạn nộp {fmtDate(data.dueAt)}</span><strong>{answered}/{data.items.length} câu đã làm</strong></div>
          <div className="bar" aria-label={`Đã làm ${answered}/${data.items.length} câu`}><span style={{ width: `${data.items.length ? (100 * answered) / data.items.length : 0}%` }} /></div>
        </header>
      )}
      {inFocus ? null : <GuestBanner />}
      {inFocus ? null : <HabitBar assignmentId={assignmentId} />}
      {hasReview && !inFocus ? <Steps stage={stage} /> : null}
      {stage === "ask" ? (
        <ReviewAsk assignmentId={assignmentId} onChoose={(c) => setView(c === "done" ? "quiz" : "review")} onSaved={reload} />
      ) : null}
      {stage === "review" ? (
        <ReviewStepper assignmentId={assignmentId} cards={review} state={rs} startId={cardId} onSaved={reload} onDone={() => setView("quiz")} />
      ) : null}
      {stage === "quiz" && hasReview && !inFocus ? (
        <p>
          <button type="button" className="review-link" onClick={() => setView("review")}>
            Xem lại phần ôn
          </button>
        </p>
      ) : null}
      {stage === "quiz" ? <PersonalizationBar focus={focus} onFocus={(on) => { setFocus(on); setIdx(0); }} /> : null}
      {prefs.nhac_tien_do && !inFocus ? (
        <p className="pers-nudge" role="status">
          Em đã làm {answered}/{data.items.length} câu{answered < data.items.length ? `, còn ${data.items.length - answered} câu nữa là xong.` : ". Giỏi lắm!"}
        </p>
      ) : null}
      {isClosed ? <Notice>Bài đã hết hạn nộp. Em vẫn xem lại được bài.</Notice> : null}
      {!isClosed && items.length > 0 && answered === items.length ? (
        <Notice tone="success">
          Em đã làm xong bài. Mỗi câu chỉ nộp một lần, để thầy cô biết em hiểu bài đến đâu ngay từ lần làm đầu. Em vẫn có thể
          xem lại lời giải và hỏi HABIT AI ở từng câu.
        </Notice>
      ) : null}
      {inFocus && cur ? (
        <section className="focus" aria-label="Chế độ tập trung">
          <div className="focus-top">
            <strong>Câu {Math.min(idx, items.length - 1) + 1}/{items.length}</strong>
            {prefs.hen_gio_tap_trung ? <FocusTimer minutes={Number(prefs.hen_gio_tap_trung)} /> : null}
          </div>
          <div className="bar" role="progressbar" aria-label="Tiến độ" aria-valuemin={0} aria-valuemax={items.length} aria-valuenow={answered}>
            <span style={{ width: `${(100 * answered) / items.length}%` }} />
          </div>
          <details className="focus-content">
            <summary>Xem lại nội dung bài</summary>
            {content.map((e) => <ContentView key={e.block.id} block={e.block} />)}
          </details>
          <ItemView key={cur.id} {...itemProps(cur, Math.min(idx, items.length - 1) + 1)} />
          <div className="focus-nav">
            <Button onClick={() => setIdx((i) => Math.max(0, i - 1))} disabled={idx <= 0}>Câu trước</Button>
            <Button variant="primary" onClick={() => setIdx((i) => Math.min(items.length - 1, i + 1))} disabled={idx >= items.length - 1}>Câu tiếp</Button>
          </div>
        </section>
      ) : null}
      {inFocus || stage !== "quiz" ? null : entries.map((e) =>
        "block" in e && e.block ? (
          <ContentView key={e.block.id} block={e.block} />
        ) : "item" in e && e.item ? (
          <ItemView key={e.item.id} {...itemProps(e.item, ++n)} />
        ) : null,
      )}
      {/* "Thank you" only once every question is answered; the code itself stays visible in the banner meanwhile. */}
      {!inFocus && items.length > 0 && answered === items.length ? <GuestSurveyCard /> : null}
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

function ItemView({ no, item, assignmentId, disabled, onAnswered, onClosed, onOpenReview }: {
  no: number;
  item: Item;
  assignmentId: string;
  disabled: boolean;
  onAnswered: () => void;
  onClosed: () => void;
  onOpenReview?: (cardId: string) => void;
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
  // "Làm lại": practice after the first attempt. Graded and explained, but teachers keep seeing the first attempt only.
  const [redo, setRedo] = useState(false);
  const [practice, setPractice] = useState<Schemas["AttemptResult"] | null>(null);
  const numeric = item.itemType === "NUMERIC" && value.trim() !== "" ? parseAnswerNumber(value) : null;

  async function submit(e: FormEvent) {
    e.preventDefault();
    let answer: Schemas["AnswerIn"];
    if (item.itemType === "MCQ") answer = { choice: choice as "A" | "B" | "C" | "D" };
    else if (item.itemType === "NUMERIC") {
      if (!numeric || !("value" in numeric)) return;
      answer = { value: numeric.value };
    }
    else answer = { text: text.trim() };
    setBusy(true);
    setError(null);
    if (redo) {
      try {
        setPractice(await unwrap(api.POST("/v1/student/assignments/{assignment_id}/practice", { params: { path: { assignment_id: assignmentId } }, body: { itemId: item.id, answer } })));
        setRedo(false);
        setChoice("");
        setValue("");
        setText("");
      } catch (err) {
        setError(err);
      } finally {
        setBusy(false);
      }
      return;
    }
    requestId.current ??= newRequestId();
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
      else if (code === "PAST_DUE" || code === "ASSIGNMENT_CLOSED") onClosed();
      if (code !== "NETWORK") requestId.current = null;
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const ready = item.itemType === "MCQ" ? !!choice : item.itemType === "NUMERIC" ? !!numeric && "value" in numeric : text.trim() !== "";
  const numericError = numeric && "error" in numeric ? numeric.error : null;
  const noteId = `note-${item.id}`;

  return (
    <section className="card item" aria-labelledby={`q-${item.id}`}>
      <div className="item-top"><span className="question-number">Câu {no}</span><span className={`skill-chip skill-${item.skill}`}>{SKILL[item.skill]}</span></div>
      <p id={`q-${item.id}`} className="stem">
        {item.stem}
      </p>
      <HabitItem assignmentId={assignmentId} itemId={item.id} answered={!!result} explanation={result?.explanation ?? null} onOpenReview={onOpenReview} />
      {result && !redo ? (
        <>
          <Result result={result} />
          {practice ? <Result result={practice} title="Lần làm lại" /> : null}
          <div>
            <Button onClick={() => { setPractice(null); setRedo(true); }}>Làm lại</Button>{" "}
            <span className="muted small">Làm lại để luyện tập. Thầy cô vẫn xem lần làm đầu của em.</span>
          </div>
        </>
      ) : (
        <form className="stack" onSubmit={submit}>
          {redo ? <p className="muted small">Lượt luyện tập: không thay đổi kết quả thầy cô thấy.</p> : null}
          {item.itemType === "MCQ" ? (
            <div className="options" role="radiogroup">
              {item.options?.map((o) => (
                <label key={o.label} className={choice === o.label ? "option on" : "option"}>
                  <input
                    type="radio"
                    name={`q-${item.id}`}
                    value={o.label}
                    checked={choice === o.label}
                    disabled={disabled && !redo}
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
              aria-invalid={numericError ? true : undefined}
              aria-describedby={noteId}
              value={value}
              disabled={disabled && !redo}
              onChange={(e) => setValue(e.target.value)}
            />
          ) : (
            <textarea
              rows={3}
              aria-label="Câu trả lời"
              value={text}
              disabled={disabled && !redo}
              onChange={(e) => setText(e.target.value)}
              maxLength={2000}
            />
          )}
          {error ? <div className="alert alert-danger" role="alert">{errorMessage(error)}</div> : null}
          <div className="submit-row">
            <Button type="submit" variant="primary" className="submit-btn" busy={busy} disabled={(disabled && !redo) || !ready}>
              {redo ? "Nộp lần làm lại" : "Nộp câu trả lời"}
            </Button>
            <span className={numericError ? "submit-note field-error" : "submit-note"} id={noteId} aria-live="polite">
              {numericError ?? (ready ? (redo ? "Lời giải hiện sau khi nộp." : "Em chỉ nộp một lần. Lời giải hiện sau khi nộp.") : item.itemType === "MCQ" ? "Chọn một đáp án để nộp." : item.itemType === "NUMERIC" ? "Nhập đáp số để nộp." : "Viết câu trả lời để nộp.")}
            </span>
          </div>
        </form>
      )}
    </section>
  );
}

function Result({ result, title }: { result: Schemas["AttemptResult"]; title?: string }) {
  const tone = result.isCorrect === true ? "success" : result.isCorrect === false ? "danger" : "info";
  const label = result.isCorrect === true ? "Đúng" : result.isCorrect === false ? "Chưa đúng" : "Đã ghi nhận câu trả lời";
  return (
    <div className={`alert alert-${tone}`} role="status">
      <strong>{title ? `${title}: ${label}` : label}</strong>
      {result.correctAnswer ? (
        <p className="answer-reveal">
          <strong>Đáp án đúng:</strong> {result.correctAnswer}
        </p>
      ) : null}
      {result.explanation ? <p className="explanation">{result.explanation}</p> : null}
      <p className="source-line muted small">{result.sourceQuote ? `Theo giáo án: ${result.sourceQuote}` : "Nguồn: tài liệu giáo viên đã duyệt"}</p>
    </div>
  );
}
