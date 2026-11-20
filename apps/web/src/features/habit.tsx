"use client";

import { useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { errorCode, errorMessage } from "@/lib/errors";
import { newRequestId } from "@/lib/uuid";
import { HabitMark, SourceRef } from "./habit-parts";
import { askHabit, habitKey, useHabit, useHabitOn, type ChatReply } from "./habit-api";

// The chat sheet is only downloaded when a student opens it.
const HabitChat = dynamic(() => import("./habit-chat"), { ssr: false });

const BADGE_HINT: Record<string, string> = {
  TU_LUC: "Đúng ngay lần đầu, không cần gợi ý",
  KIEN_TRI: "Học 3 ngày liên tiếp",
  THAM_HIEM: "Đọc phần nguồn rồi làm đúng",
};

export function HabitBar({ assignmentId }: { assignmentId: string }) {
  const on = useHabitOn();
  const h = useHabit(assignmentId, on);
  if (!on || !h.data) return null;
  const { streak, todayDone, todayGoal, badges } = h.data;
  const done = Math.min(todayDone, todayGoal);
  return (
    <section className="habit-bar" aria-label="Thói quen học của em">
      <span className="habit-streak">
        <span aria-hidden="true">🔥</span> {streak} ngày liên tiếp
      </span>
      <span className="habit-goal">
        <span>
          Mục tiêu hôm nay {done}/{todayGoal}
        </span>
        <span className="bar" role="progressbar" aria-valuemin={0} aria-valuemax={todayGoal} aria-valuenow={done} aria-label="Mục tiêu hôm nay">
          <span style={{ width: `${todayGoal ? (100 * done) / todayGoal : 0}%` }} />
        </span>
      </span>
      {badges.length ? (
        <ul className="habit-badges">
          {badges.map((b) => (
            <li key={b.code} title={BADGE_HINT[b.code]}>
              <HabitMark /> {b.label}
            </li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}

/** Hint card + "Hỏi Habit" for one item. Own state, so a chat message never re-renders the whole assignment. */
export function HabitItem({ assignmentId, itemId, answered, explanation }: {
  assignmentId: string;
  itemId: string;
  answered: boolean;
  explanation: string | null;
}) {
  const on = useHabitOn();
  const qc = useQueryClient();
  const h = useHabit(assignmentId, on && !answered);
  const [hints, setHints] = useState<ChatReply[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<unknown>(null);
  const [open, setOpen] = useState(false);
  const [mounted, setMounted] = useState(false);
  const rid = useRef<string | null>(null);
  const close = useCallback(() => setOpen(false), []);
  if (!on) return null;

  const server = h.data?.hintsAvailable.find((x) => x.itemId === itemId)?.hintsUsed ?? 0;
  const used = Math.max(hints.length, server);
  const limited = errorCode(err) === "CHAT_LIMIT";
  const openChat = () => {
    setMounted(true);
    setOpen(true);
  };

  async function hint() {
    rid.current ??= newRequestId();
    setBusy(true);
    setErr(null);
    try {
      const r = await askHabit(assignmentId, { itemId, action: "hint", requestId: rid.current });
      rid.current = null;
      setHints((x) => [...x, r]);
      void qc.invalidateQueries({ queryKey: habitKey(assignmentId) });
    } catch (e) {
      if (errorCode(e) !== "NETWORK") rid.current = null;
      setErr(e);
    } finally {
      setBusy(false);
    }
  }

  const chat = mounted ? (
    <HabitChat assignmentId={assignmentId} itemId={itemId} answered={answered} explanation={explanation} open={open} onClose={close} />
  ) : null;

  if (answered) {
    return (
      <div className="habit">
        <div className="habit-actions">
          <Button variant="secondary" className="habit-btn" onClick={openChat}>
            <HabitMark /> Habit giải thích
          </Button>
        </div>
        {chat}
      </div>
    );
  }
  return (
    <div className="habit">
      <div className="habit-actions">
        <Button variant="secondary" className="habit-btn" onClick={() => void hint()} busy={busy} disabled={used >= 3 || limited}>
          <HabitMark /> {used >= 3 ? "Gợi ý 3/3 (đã dùng hết)" : `Gợi ý ${used + 1}/3`}
        </Button>
        <Button variant="secondary" className="habit-btn" onClick={openChat}>
          <HabitMark /> Hỏi Habit
        </Button>
      </div>
      <div aria-live="polite">
        {hints.map((x, i) => (
          <div key={i} className="habit-hint">
            <strong>Gợi ý {x.hintLevel}/3</strong>
            <p>{x.reply}</p>
            {x.sourceRefs.map((s) => (
              <SourceRef key={s.blockId} label={s.label} excerpt={s.excerpt} />
            ))}
          </div>
        ))}
        {limited ? (
          <div className="habit-limit" role="status">
            Hôm nay em hỏi nhiều rồi, thử tự làm nhé!
          </div>
        ) : null}
        {err && !limited ? (
          <div className="alert alert-danger" role="alert">
            {errorMessage(err)}{" "}
            <Button variant="secondary" onClick={() => void hint()}>
              Thử lại
            </Button>
          </div>
        ) : null}
      </div>
      {chat}
    </div>
  );
}
