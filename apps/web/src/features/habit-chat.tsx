"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
import { Button } from "@/components/ui";
import { errorCode, errorMessage } from "@/lib/errors";
import { newRequestId } from "@/lib/uuid";
import { askHabit, type ChatReply } from "./habit-api";
import { HabitMark, SourceRef } from "./habit-parts";

const QUICK = ["Em nên bắt đầu từ đâu?", "Số liệu này nằm ở đâu?", "Công thức tính là gì?"];
const MAX = 300;
type Msg = { id: number; from: "me" | "habit"; text: string; refs?: ChatReply["sourceRefs"]; refused?: boolean };

/** Bottom sheet (narrow) / side panel (wide). Plain text only: replies are rendered as React text, never as HTML. */
export default function HabitChat({ assignmentId, itemId, answered, explanation, open, onClose }: {
  assignmentId: string;
  itemId: string;
  answered: boolean;
  explanation: string | null;
  open: boolean;
  onClose: () => void;
}) {
  const dlg = useRef<HTMLDialogElement>(null);
  const log = useRef<HTMLDivElement>(null);
  const seq = useRef(0);
  const retry = useRef<{ text: string; rid: string } | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>(() => (answered && explanation ? [{ id: 0, from: "habit", text: explanation }] : []));
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const limited = errorCode(err) === "CHAT_LIMIT";

  useEffect(() => {
    const d = dlg.current;
    if (!d) return;
    if (open && !d.open) {
      // Wide screens: a side panel that does not block the page (Nộp stays clickable). Narrow: modal sheet (focus trap + Esc).
      if (window.matchMedia("(min-width: 1100px)").matches) d.show();
      else d.showModal();
    }
    if (!open && d.open) d.close();
  }, [open]);

  useEffect(() => {
    // Non-modal side panel: Esc must work even when focus fell back to the page (e.g. the button just got disabled).
    if (!open) return;
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [open, onClose]);

  useEffect(() => {
    // scrollTop on the log itself: scrollIntoView also scrolls the page/dialog in WebKit
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [msgs, busy]);

  async function send(message: string) {
    const m = message.trim();
    if (!m) return;
    const r = retry.current && retry.current.text === m ? retry.current : { text: m, rid: newRequestId() };
    const first = retry.current?.text !== m;
    retry.current = r;
    setBusy(true);
    setErr(null);
    if (m === text.trim()) setText(""); // clear now, not on success: the student may already be typing the next question
    if (first) setMsgs((x) => [...x, { id: ++seq.current, from: "me", text: m }]);
    try {
      const res = await askHabit(assignmentId, { itemId, action: "ask", message: m, requestId: r.rid });
      retry.current = null;
      setMsgs((x) => [...x, { id: ++seq.current, from: "habit", text: res.reply, refs: res.sourceRefs, refused: !!res.blockedReason }]);
    } catch (e) {
      if (errorCode(e) !== "NETWORK") retry.current = null;
      setErr(e);
    } finally {
      setBusy(false);
    }
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!busy && !limited) void send(text);
  }

  return (
    <dialog ref={dlg} className="habit-sheet" aria-label="Hỏi Habit" onClose={onClose}>
      <header className="habit-sheet-head">
        <strong>
          <HabitMark /> Habit
        </strong>
        <button type="button" className="habit-close" onClick={onClose} aria-label="Đóng Habit">
          ×
        </button>
      </header>
      <p className="habit-note">Habit không đưa đáp án — em tự làm nhé! Không nhập thông tin cá nhân.</p>
      <div ref={log} className="habit-log" aria-live="polite" aria-busy={busy}>
        {msgs.map((m) => (
          <div key={m.id} className={`habit-msg ${m.from}${m.refused ? " refused" : ""}`}>
            <p>{m.text}</p>
            {m.refs?.map((s) => (
              <SourceRef key={s.blockId} label={s.label} excerpt={s.excerpt} />
            ))}
          </div>
        ))}
        {busy ? <div className="habit-msg habit habit-think">Habit đang nghĩ…</div> : null}
        {limited ? (
          <div className="habit-limit" role="status">
            Hôm nay em hỏi nhiều rồi, thử tự làm nhé!
          </div>
        ) : null}
        {err && !limited ? (
          <div className="alert alert-danger" role="alert">
            {errorMessage(err)}{" "}
            <Button variant="secondary" onClick={() => void send(retry.current?.text ?? text)}>
              Thử lại
            </Button>
          </div>
        ) : null}
      </div>
      {!answered ? (
        <form className="habit-form" onSubmit={submit}>
          <div className="habit-chips">
            {QUICK.map((q) => (
              <button key={q} type="button" className="habit-chip" disabled={busy || limited} onClick={() => void send(q)}>
                {q}
              </button>
            ))}
          </div>
          <div className="habit-input">
            <textarea
              rows={2}
              value={text}
              maxLength={MAX}
              placeholder="Em muốn hỏi gì về bài này…"
              autoComplete="off"
              aria-label="Câu hỏi cho Habit"
              disabled={limited}
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(e);
                }
              }}
            />
            <Button type="submit" variant="primary" disabled={busy || limited || !text.trim()}>
              Gửi
            </Button>
          </div>
          <p className="habit-count" aria-hidden="true">
            {text.length}/{MAX}
          </p>
        </form>
      ) : null}
    </dialog>
  );
}
