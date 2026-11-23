"use client";

import { usePathname } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { useTheme } from "@/lib/theme";
import { answerChip, answerFaq, chipLabel, START_CHIPS, type FaqAction, type FaqAnswer, type FaqContext } from "./faq";
import { SeedPicker } from "./seed-picker";
import { stageFor, type Progress, type Species } from "./species";
import { PICKER_EVENT, TOUR_EVENT, useGarden, useProgress } from "./store";
import { Tour, type TourName } from "./tour";
import { MascotAvatar } from "./tree";

const DISMISS_KEY = "preclass.garden.later"; // "Để sau" on the first picker: ask again next session, not on every page

function tourFor(path: string): TourName | null {
  if (path === "/student") return "home";
  if (path.startsWith("/student/assignments/")) return "assignment";
  return null;
}
// The tour starts once its page has drawn its main parts (data arrives after the first render).
const READY_TARGET: Record<TourName, string> = { home: "garden", assignment: "submit" };

/**
 * Everything around the student's mascot, mounted once in the student layout:
 * the seed picker (first visit), the guided tours, and the floating mascot with its how-to chat.
 */
export function StudentCompanion() {
  const path = usePathname();
  const { ready, species, tours, choose, markTour } = useGarden();
  const progress = useProgress();
  const stage = stageFor(progress?.done ?? 0);
  const [picker, setPicker] = useState(false);
  const [tour, setTour] = useState<TourName | null>(null);
  const page = tourFor(path);

  // First visit: open the picker unless the student said "Để sau" in this session.
  useEffect(() => {
    if (!ready || species) return;
    let later = false;
    try {
      later = sessionStorage.getItem(DISMISS_KEY) === "1";
    } catch {
      /* blocked storage: ask */
    }
    if (!later) setPicker(true);
  }, [ready, species]);

  useEffect(() => {
    const openPicker = () => setPicker(true);
    const openTour = () => page && setTour(page);
    window.addEventListener(PICKER_EVENT, openPicker);
    window.addEventListener(TOUR_EVENT, openTour);
    return () => {
      window.removeEventListener(PICKER_EVENT, openPicker);
      window.removeEventListener(TOUR_EVENT, openTour);
    };
  }, [page]);

  // A page's tour runs by itself the first time (right after planting, for the home page).
  useEffect(() => {
    if (!ready || !species || !page || picker || tours.includes(page)) return;
    let n = 0;
    const id = window.setInterval(() => {
      n++;
      if (document.querySelector(`[data-tour="${READY_TARGET[page]}"]`) || n > 12) {
        window.clearInterval(id);
        setTour(page);
      }
    }, 300);
    return () => window.clearInterval(id);
  }, [ready, species, page, picker, tours]);

  const closeTour = useCallback(() => {
    if (tour) markTour(tour);
    setTour(null);
  }, [tour, markTour]);

  const closePicker = useCallback(() => {
    setPicker(false);
    if (!species) {
      try {
        sessionStorage.setItem(DISMISS_KEY, "1");
      } catch {
        /* blocked */
      }
    }
  }, [species]);

  return (
    <>
      {ready ? (
        <SeedPicker
          open={picker}
          current={species?.id ?? null}
          onClose={closePicker}
          onChoose={(id) => {
            choose(id);
            setPicker(false);
          }}
        />
      ) : null}
      {species && tour ? <Tour name={tour} species={species} stage={stage} open onClose={closeTour} /> : null}
      {species ? <MascotDock species={species} stage={stage} progress={progress} onAssignment={page === "assignment"} /> : null}
    </>
  );
}

type Msg = { id: number; from: "me" | "mascot"; text: string; actions?: FaqAnswer["actions"]; follow?: string[] };

function MascotDock({ species, stage, progress, onAssignment }: {
  species: Species;
  stage: number;
  progress: Progress | null;
  onAssignment: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const seq = useRef(0);
  const log = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);
  const { toggle } = useTheme();
  const ctx: FaqContext = { species, progress, onAssignment };

  useEffect(() => {
    if (!open) return;
    if (msgs.length === 0) {
      const greet = progress && progress.streak > 0 ? `${species.hello} Em đang có chuỗi ${progress.streak} bài liên tiếp.` : species.hello;
      setMsgs([{ id: ++seq.current, from: "mascot", text: `${greet} Em cần mình chỉ gì về cách dùng app?`, follow: [...START_CHIPS] }]);
    }
    input.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps -- greet only when first opened

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [msgs]);

  function reply(question: string, a: FaqAnswer) {
    setMsgs((x) => [...x, { id: ++seq.current, from: "me", text: question }, { id: ++seq.current, from: "mascot", text: a.text, actions: a.actions, follow: a.follow }]);
  }

  function act(a: FaqAction) {
    if (a === "theme") return toggle();
    setOpen(false);
    window.dispatchEvent(new Event(a === "tour" ? TOUR_EVENT : PICKER_EVENT));
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const q = text.trim();
    if (!q) return;
    setText("");
    reply(q, answerFaq(q, ctx));
  }

  return (
    <div className="mascot-dock" style={{ ["--mascot" as string]: species.accent }}>
      {open ? (
        <section className="mascot-panel" role="dialog" aria-label={`Hỏi ${species.mascot} cách dùng`}>
          <header className="mascot-panel-head">
            <MascotAvatar species={species} stage={stage} size={44} />
            <div>
              <strong>{species.mascot}</strong>
              <span className="muted small">Người đồng hành · hướng dẫn sử dụng</span>
            </div>
            <button type="button" className="habit-close" onClick={() => setOpen(false)} aria-label={`Đóng ${species.mascot}`}>
              ×
            </button>
          </header>
          <div ref={log} className="mascot-log" aria-live="polite">
            {msgs.map((m, idx) => (
              <div key={m.id} className={`mascot-msg ${m.from}`}>
                {m.from === "mascot" ? <MascotAvatar species={species} stage={stage} size={28} /> : null}
                <div className="mascot-bubble">
                  <p>{m.text}</p>
                  {m.actions?.length ? (
                    <div className="mascot-actions">
                      {m.actions.map((a) => (
                        <button key={a.action} type="button" className="btn btn-primary" onClick={() => act(a.action)}>
                          {a.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                  {m.follow?.length && idx === msgs.length - 1 ? (
                    <div className="mascot-chips" role="group" aria-label="Em có thể hỏi">
                      {m.follow.map((id) => (
                        <button key={id} type="button" className="habit-chip" onClick={() => reply(chipLabel(id), answerChip(id, ctx))}>
                          {chipLabel(id)}
                        </button>
                      ))}
                    </div>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
          <form className="mascot-form" onSubmit={submit}>
            <input
              ref={input}
              value={text}
              maxLength={200}
              onChange={(e) => setText(e.target.value)}
              placeholder="Hỏi cách dùng, ví dụ: gợi ý dùng sao?"
              aria-label={`Câu hỏi cho ${species.mascot}`}
              autoComplete="off"
            />
            <button type="submit" className="btn btn-primary" disabled={!text.trim()}>
              Gửi
            </button>
          </form>
          <p className="mascot-note">Hỏi về bài học? Bấm “Hỏi HABIT AI” trong từng câu nhé.</p>
        </section>
      ) : null}
      <button
        type="button"
        className={`mascot-fab${open ? " on" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? `Thu gọn ${species.mascot}` : `Hỏi ${species.mascot}: hướng dẫn sử dụng`}
        data-tour="mascot"
      >
        <MascotAvatar species={species} stage={stage} size={58} className="mascot-bob" />
        <span className="mascot-fab-name">{species.mascot}</span>
      </button>
    </div>
  );
}
