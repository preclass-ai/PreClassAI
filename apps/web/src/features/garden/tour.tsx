"use client";

import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";
import type { Species } from "./species";
import { MascotAvatar } from "./tree";

/** One stop of the tour: a [data-tour] target on the page (skipped when absent) and what the mascot says there. */
export interface TourStep {
  target?: string;
  title: string;
  text: string;
}

export type TourName = "home" | "assignment";

export function tourSteps(name: TourName, s: Species): TourStep[] {
  if (name === "home") {
    return [
      { title: `Chào em, mình là ${s.mascot}!`, text: `${s.hello} Mình dẫn em đi một vòng xem trang này có gì nhé.` },
      { target: "nav", title: "Thanh điều hướng", text: "“Bài của em” luôn đưa em về trang này, nơi có mọi bài thầy cô giao." },
      { target: "garden", title: "Khu vườn của em", text: `Đây là nhà của mình. Mỗi bài em làm xong trước hạn, mình lớn thêm và chuỗi 🔥 tăng 1. Cuối tuần hay nghỉ lễ không có bài thì chuỗi vẫn giữ. Mình qua ${s.stages.length} giai đoạn từ “${s.stages[0]}” tới “${s.stages[s.stages.length - 1]}”.` },
      { target: "strip", title: "Tổng quan", text: "Số bài em còn phải làm và số bài đã xong." },
      { target: "assignments", title: "Bài được giao", text: "Bấm vào một thẻ để làm bài. Thẻ ghi hạn nộp và em đã làm bao nhiêu câu." },
      { target: "theme", title: "Sáng hay tối", text: "Học buổi tối thì bật giao diện tối cho đỡ chói mắt. App sẽ nhớ lựa chọn của em." },
      { target: "mascot", title: "Mình luôn ở đây", text: "Bấm vào mình bất cứ lúc nào để hỏi cách dùng app. Còn khi làm bài, bấm “Hỏi HABIT AI” trong câu hỏi là mình vào cùng suy nghĩ với em." },
    ];
  }
  return [
    { title: "Vào bài rồi!", text: `${s.mascot} chỉ nhanh các phần của trang làm bài nhé.` },
    { target: "habit-bar", title: "Thói quen học", text: "Chuỗi bài của em, còn mấy câu nữa là xong bài này, và huy hiệu em đã có. Xong bài trước hạn là chuỗi tăng thêm 1." },
    { target: "pers", title: "Cách học hôm nay", text: "Chọn kiểu gợi ý em thích, bật chế độ tập trung để làm từng câu một, hoặc hẹn giờ." },
    { target: "hint", title: "Gợi ý từng bậc", text: "Kẹt thì bấm gợi ý: mỗi lần một bậc, cụ thể dần. Mỗi câu có số lượt giới hạn, nên thử tự nghĩ trước nha." },
    { target: "ask-ai", title: "Hỏi HABIT AI", text: `Bấm đây là ${s.mascot} vào khung trò chuyện, cùng em phân tích đúng câu này. Mình không nói đáp án, nhưng sẽ chỉ chỗ số liệu và cách nghĩ.` },
    { target: "submit", title: "Nộp câu trả lời", text: "Mỗi câu nộp một lần. Nộp xong em xem được lời giải thầy cô đã duyệt, và có thể “Làm lại” để luyện thêm." },
    { target: "mascot", title: "Cần gì cứ gọi mình", text: "Mình ở góc này. Chúc em làm bài tốt!" },
  ];
}

interface Rect { top: number; left: number; width: number; height: number }

function findTarget(name?: string): HTMLElement | null {
  if (!name) return null;
  const all = Array.from(document.querySelectorAll<HTMLElement>(`[data-tour="${name}"]`));
  return all.find((el) => el.getClientRects().length > 0) ?? null; // first visible one
}

/**
 * Spotlight tour. The page behind is dimmed and not clickable; Esc or "Bỏ qua" ends it.
 * Steps whose target is not on the page (e.g. no assignments yet) are skipped.
 */
export function Tour({ name, species, stage, open, onClose }: { name: TourName; species: Species; stage: number; open: boolean; onClose: () => void }) {
  const [steps, setSteps] = useState<TourStep[]>([]);
  const [i, setI] = useState(0);
  const [rect, setRect] = useState<Rect | null>(null);
  const card = useRef<HTMLDivElement>(null);
  const [cardPos, setCardPos] = useState<{ top: number; left: number } | null>(null);

  useEffect(() => {
    if (!open) return;
    setSteps(tourSteps(name, species).filter((s) => !s.target || findTarget(s.target)));
    setI(0);
  }, [open, name, species]);

  const step = steps[i];
  const measure = useCallback(() => {
    const el = findTarget(step?.target);
    if (!el) return setRect(null);
    const r = el.getBoundingClientRect();
    const pad = 8;
    setRect({ top: r.top - pad, left: r.left - pad, width: r.width + 2 * pad, height: r.height + 2 * pad });
  }, [step]);

  useEffect(() => {
    if (!open || !step) return;
    const el = findTarget(step.target);
    const reduce = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
    if (el) {
      // Center the target; a tall one goes to the top (under the sticky bar) so the card fits below it.
      const r = el.getBoundingClientRect();
      const bar = document.querySelector(".topbar")?.getBoundingClientRect().height ?? 0;
      const tall = r.height > window.innerHeight * 0.4;
      const y = window.scrollY + r.top - (tall ? bar + 16 : (window.innerHeight - r.height) / 2);
      window.scrollTo({ top: Math.max(0, y), behavior: reduce ? "auto" : "smooth" });
    }
    measure();
    const t = window.setTimeout(measure, 350); // after smooth scroll
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    return () => {
      window.clearTimeout(t);
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
    };
  }, [open, step, measure]);

  useLayoutEffect(() => {
    // Card beside the spotlight: below if there is room, else above; centered when there is no target.
    const c = card.current;
    if (!open || !c) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const w = c.offsetWidth;
    const h = c.offsetHeight;
    if (!rect) return setCardPos({ top: Math.max(16, (vh - h) / 2), left: Math.max(12, (vw - w) / 2) });
    const below = rect.top + rect.height + 14;
    const top = below + h < vh - 12 ? below : Math.max(12, rect.top - h - 14);
    const left = Math.min(Math.max(12, rect.left + rect.width / 2 - w / 2), vw - w - 12);
    setCardPos({ top, left });
  }, [rect, open, i, steps.length]);

  useEffect(() => {
    if (!open) return;
    card.current?.focus();
    const key = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
      if (e.key === "ArrowRight") setI((x) => Math.min(x + 1, steps.length - 1));
      if (e.key === "ArrowLeft") setI((x) => Math.max(x - 1, 0));
    };
    document.addEventListener("keydown", key);
    return () => document.removeEventListener("keydown", key);
  }, [open, onClose, steps.length]);

  if (!open || !step) return null;
  const last = i === steps.length - 1;

  return (
    <div className="tour" style={{ ["--mascot" as string]: species.accent }}>
      <div className="tour-blocker" onClick={(e) => e.stopPropagation()} />
      {rect ? (
        <div className="tour-spot" style={{ top: rect.top, left: rect.left, width: rect.width, height: rect.height }} aria-hidden="true" />
      ) : (
        <div className="tour-dim" aria-hidden="true" />
      )}
      <div
        ref={card}
        className="tour-card"
        role="dialog"
        aria-modal="true"
        aria-label="Hướng dẫn sử dụng"
        tabIndex={-1}
        style={cardPos ? { top: cardPos.top, left: cardPos.left } : { visibility: "hidden" }}
      >
        <div className="tour-card-head">
          <MascotAvatar species={species} stage={stage} size={46} className="mascot-bob" />
          <div>
            <strong>{step.title}</strong>
            <span className="tour-count">
              {species.mascot} · {i + 1}/{steps.length}
            </span>
          </div>
        </div>
        <p aria-live="polite">{step.text}</p>
        <div className="tour-dots" aria-hidden="true">
          {steps.map((_, k) => (
            <i key={k} className={k === i ? "on" : undefined} />
          ))}
        </div>
        <div className="tour-actions">
          <button type="button" className="link-btn" onClick={onClose}>
            {last ? "Đóng" : "Bỏ qua"}
          </button>
          <span className="spacer" />
          {i > 0 ? (
            <button type="button" className="btn btn-ghost" onClick={() => setI(i - 1)}>
              Trước
            </button>
          ) : null}
          <button type="button" className="btn btn-primary" onClick={() => (last ? onClose() : setI(i + 1))} autoFocus>
            {last ? "Xong rồi!" : "Tiếp"}
          </button>
        </div>
      </div>
    </div>
  );
}
