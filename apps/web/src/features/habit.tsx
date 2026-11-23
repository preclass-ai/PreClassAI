"use client";

import { useQueryClient } from "@tanstack/react-query";
import dynamic from "next/dynamic";
import { useCallback, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { errorCode, errorMessage } from "@/lib/errors";
import { newRequestId } from "@/lib/uuid";
import { HabitMark, HintIcon, SourceRef } from "./habit-parts";
import { progressOf, stageFor } from "./garden/species";
import { streakIfDone, useAssignmentList, useMascot, useProgress } from "./garden/store";
import { MascotAvatar } from "./garden/tree";
import { hintTier } from "@/lib/labels";
import { usePersonalizationOn, usePrefs } from "./personalization";
import { askHabit, habitKey, useHabit, useHabitOn, type ChatReply } from "./habit-api";

// The chat sheet is only downloaded when a student opens it.
const HabitChat = dynamic(() => import("./habit-chat"), { ssr: false });

const BADGE_HINT: Record<string, string> = {
  TU_LUC: "Đúng ngay lần đầu, không cần gợi ý",
  KIEN_TRI: "Học 3 ngày liên tiếp", // computed by the server on calendar days (backend follow-up: move to the assignment streak)
  THAM_HIEM: "Đọc phần nguồn rồi làm đúng",
};

/**
 * What this assignment does for the streak: the streak counts finished assignments (never calendar days), so the bar
 * says how many questions are left before it goes up. Badges come from HABIT and show only when it is on.
 */
export function HabitBar({ assignmentId, answered, total, closed }: { assignmentId: string; answered: number; total: number; closed: boolean }) {
  const on = useHabitOn();
  const h = useHabit(assignmentId, on);
  const items = useAssignmentList();
  const species = useMascot();
  if (!items || total === 0) return null;
  const { streak, done } = progressOf(items);
  const after = streakIfDone(items, assignmentId);
  const left = Math.max(0, total - answered);
  const badges = h.data?.badges ?? [];
  const next =
    left === 0
      ? "Em đã xong bài này, chuỗi đã được tính."
      : closed
        ? "Bài này đã hết hạn. Chuỗi bắt đầu lại từ bài tiếp theo, cây của em vẫn giữ nguyên."
        : after > streak
          ? `Còn ${left} câu nữa là xong bài, chuỗi lên 🔥 ${after}.`
          : `Còn ${left} câu nữa là xong bài, cây của em lớn thêm.`;
  return (
    <section className="habit-bar" aria-label="Thói quen học của em" data-tour="habit-bar" style={species ? { ["--mascot" as string]: species.accent } : undefined}>
      {species ? <MascotAvatar species={species} stage={stageFor(done)} size={36} /> : null}
      <span className="habit-streak">
        <span aria-hidden="true">🔥</span> {streak > 0 ? `Chuỗi ${streak} bài` : "Chưa có chuỗi"}
      </span>
      <span className="habit-next">{next}</span>
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

/** Hint card + "Hỏi HABIT AI" for one item. Own state, so a chat message never re-renders the whole assignment. */
export function HabitItem({ assignmentId, itemId, answered, explanation, onOpenReview }: {
  assignmentId: string;
  itemId: string;
  answered: boolean;
  explanation: string | null;
  onOpenReview?: (cardId: string) => void;
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
  const persOn = usePersonalizationOn();
  const prefs = usePrefs(persOn);
  const close = useCallback(() => setOpen(false), []);
  // The seed the student planted speaks for HABIT AI here, at the stage their finished assignments have grown it to.
  const species = useMascot();
  const progress = useProgress();
  const mascot = species ? { species, stage: stageFor(progress?.done ?? 0) } : null;
  const aiIcon = mascot ? <MascotAvatar species={mascot.species} stage={mascot.stage} size={26} /> : <HabitMark />;
  if (!on) return null;

  const info = h.data?.hintsAvailable.find((x) => x.itemId === itemId);
  const server = info?.hintsUsed ?? 0;
  const used = Math.max(hints.length, server);
  const max = info?.hintsMax ?? 10;
  const limited = errorCode(err) === "HINT_LIMIT"; // hint presses have their own limit, apart from the chat limit
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
    <HabitChat assignmentId={assignmentId} itemId={itemId} answered={answered} explanation={explanation} open={open} onClose={close} onOpenReview={onOpenReview} mascot={mascot} />
  ) : null;

  if (answered) {
    return (
      <div className="habit">
        <div className="habit-actions">
          <Button variant={prefs.uu_tien_giai_thich ? "primary" : "ghost"} className={prefs.uu_tien_giai_thich ? "habit-btn" : "habit-ghost"} onClick={openChat} data-tour="ask-ai">
            {aiIcon} HABIT AI giải thích
          </Button>
        </div>
        {chat}
      </div>
    );
  }
  return (
    <div className={`habit${info?.advice === "QUIET" ? " quiet" : ""}`}>
      {info?.advice === "REVIEW" && info.preview ? (
        <div className="habit-advice" role="note">
          <strong>Gợi ý cho em:</strong> xem lại phần nội dung của bài trước khi làm câu này.
          <p className="habit-preview">
            <strong>{hintTier(1)}:</strong> {info.preview}
          </p>
        </div>
      ) : null}
      <div className="habit-actions">
        <Button variant="ghost" className="habit-ghost" onClick={() => void hint()} busy={busy} disabled={used >= max || limited} data-tour="hint">
          <HintIcon /> {used >= max ? "Đã dùng hết gợi ý" : `${hintTier(used + 1)} · còn ${max - used} lượt`}
        </Button>
        <Button variant="ghost" className="habit-ghost" onClick={openChat} data-tour="ask-ai">
          {aiIcon} Hỏi HABIT AI
        </Button>
      </div>
      <div aria-live="polite">
        {hints.map((x, i) => (
          <div key={i} className="habit-hint">
            <strong>
              {hintTier(x.hintsUsed ?? x.hintLevel)} · {x.hintsUsed ?? x.hintLevel}/{max}
            </strong>
            <p>{x.reply}</p>
            {x.sourceRefs.map((s) => (
              <SourceRef key={s.blockId} label={s.label} excerpt={s.excerpt} />
            ))}
            {x.openReview && onOpenReview ? (
              <Button variant="secondary" onClick={() => onOpenReview(x.openReview as string)}>
                Mở thẻ ôn
              </Button>
            ) : null}
          </div>
        ))}
        {limited ? (
          <div className="habit-limit" role="status">
            {errorMessage(err)}
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
