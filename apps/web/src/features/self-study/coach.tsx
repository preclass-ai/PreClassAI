"use client";

import { useEffect, useRef, useState, type ReactNode } from "react";
import { MascotAvatar } from "@/features/garden/tree";
import type { Species } from "@/features/garden/species";
import type { Method } from "./methods";

/**
 * The student's mascot walks them through one study method, a step at a time. "Xong bước này" ticks the step
 * (same ticks as the card) and moves on; the last step ends with the mascot's cheer.
 */
const NUDGES = [
  "Không cần vội, làm chậm mà chắc nha.",
  "Làm được bước này là em đã hơn hôm qua rồi đó.",
  "Kẹt chỗ nào thì quay lại đọc đúng chỗ đó thôi.",
  "Viết ra giấy giúp em nhớ lâu hơn chỉ nghĩ trong đầu.",
  "Gần xong rồi, cố thêm chút nữa!",
];

export function coachLine(m: Method, step: number, guide: string): string {
  if (step === 0) return `${guide} cùng em thử ${m.name} nhé. ${m.why}`;
  if (step === m.steps.length - 1) return "Bước cuối rồi! Xong bước này là em đã thử trọn một cách học.";
  return NUDGES[(step - 1) % NUDGES.length] ?? NUDGES[0]!;
}

export function MethodCoach({ method: m, species, stage, done, onTick, onClose, extra }: {
  method: Method;
  species: Species | null;
  stage: number;
  done: number[];
  onTick: (step: number, value: boolean) => void;
  onClose: () => void;
  extra?: (step: number) => ReactNode; // e.g. the focus timer on the Pomodoro step that needs it
}) {
  const firstOpen = m.steps.findIndex((_, i) => !done.includes(i));
  const [i, setI] = useState(firstOpen < 0 ? 0 : firstOpen);
  const [finished, setFinished] = useState(false);
  const card = useRef<HTMLDivElement>(null);
  const guide = species?.mascot ?? "PreClass";
  const step = m.steps[i] ?? m.steps[0]!;
  const last = i === m.steps.length - 1;

  useEffect(() => {
    card.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [onClose]);

  function next() {
    onTick(i, true);
    if (last) setFinished(true);
    else setI(i + 1);
  }

  const avatar = species ? <MascotAvatar species={species} stage={stage} size={52} className="mascot-bob" /> : <span className="ss-pick-icon" aria-hidden="true">💡</span>;

  return (
    <div className="coach-backdrop" onClick={onClose}>
      <div
        ref={card}
        className="coach"
        role="dialog"
        aria-modal="true"
        aria-label={`${guide} hướng dẫn ${m.name}`}
        tabIndex={-1}
        style={{ ["--mascot" as string]: species?.accent ?? "var(--primary)" }}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="coach-head">
          {avatar}
          <div>
            <strong>{m.name}</strong>
            <span className="tour-count">{guide} hướng dẫn · {finished ? "Hoàn thành" : `Bước ${i + 1}/${m.steps.length}`}</span>
          </div>
          <button type="button" className="habit-close" onClick={onClose} aria-label="Đóng hướng dẫn">×</button>
        </div>
        {finished ? (
          <div className="coach-body" aria-live="polite">
            <p className="coach-say">{species ? species.cheer : "Tuyệt! Em đã thử trọn cách học này."} Em đã đi hết {m.steps.length} bước của {m.name}. Lần sau dùng nó với bài được giao nhé!</p>
            <div className="tour-actions">
              <span className="spacer" />
              <button type="button" className="btn btn-primary" onClick={onClose} autoFocus>Xong rồi!</button>
            </div>
          </div>
        ) : (
          <div className="coach-body">
            <p className="coach-say">{coachLine(m, i, guide)}</p>
            <div className="coach-step" aria-live="polite">
              <b>{step.title}</b>
              <p>{step.text}</p>
              {i === 0 ? <p className="ss-geo small"><span aria-hidden="true">🗺️</span> {m.geo}</p> : null}
              {extra?.(i)}
            </div>
            <div className="tour-dots" aria-hidden="true">
              {m.steps.map((_, k) => (
                <i key={k} className={k === i ? "on" : done.includes(k) ? "done" : undefined} />
              ))}
            </div>
            <div className="tour-actions">
              <button type="button" className="link-btn" onClick={onClose}>Để sau</button>
              <span className="spacer" />
              {i > 0 ? <button type="button" className="btn btn-ghost" onClick={() => setI(i - 1)}>Trước</button> : null}
              <button type="button" className="btn btn-primary" onClick={next} autoFocus>
                {last ? "Hoàn thành ✓" : "Xong bước này ✓"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
