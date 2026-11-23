"use client";

import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useRef, useState, type FormEvent } from "react";
import { SpotlightTour } from "@/features/garden/tour";
import { INSTALL_ANCHOR } from "@/features/install-app";
import { useTheme } from "@/lib/theme";
import { answerChip, answerGuide, chipLabel, START_CHIPS, teacherTourSteps, tourFor, type GuideAction, type GuideAnswer } from "./faq";
import { GlobeMascot, GUIDE_ACCENT, GUIDE_NAME } from "./globe-mascot";

/**
 * Bé Cầu, the teachers' guide (replaces the "3 bước bắt đầu" box): a floating globe that answers how-to questions and
 * walks through the page. The tour of a page runs by itself the first time a teacher opens it.
 * What was seen is kept in this browser only; blocked storage just means the tour may show again.
 */
const SEEN_KEY = "preclass.teacher-guide.tours";
// The tour waits until the page drew the part it starts with (data arrives after the first render).
const READY: Record<string, string> = { lessons: "lesson-table", classes: "class-tabs" };

function readSeen(): string[] {
  try {
    const v = JSON.parse(localStorage.getItem(SEEN_KEY) ?? "[]") as unknown;
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string") : [];
  } catch {
    return [];
  }
}

function markSeen(name: string) {
  try {
    const seen = readSeen();
    if (!seen.includes(name)) localStorage.setItem(SEEN_KEY, JSON.stringify([...seen, name]));
  } catch {
    /* blocked */
  }
}

export function TeacherCompanion() {
  const path = usePathname();
  const page = tourFor(path);
  const [tour, setTour] = useState(false);

  useEffect(() => {
    if (page === "page" || readSeen().includes(page)) return;
    let n = 0;
    const id = window.setInterval(() => {
      n++;
      if (document.querySelector(`[data-tour="${READY[page]}"]`) || n > 15) {
        window.clearInterval(id);
        setTour(true);
      }
    }, 300);
    return () => window.clearInterval(id);
  }, [page]);

  const close = useCallback(() => {
    markSeen(page);
    setTour(false);
  }, [page]);

  return (
    <>
      <SpotlightTour
        tourKey={page}
        steps={() => teacherTourSteps(page)}
        guide={GUIDE_NAME}
        accent={GUIDE_ACCENT}
        avatar={<GlobeMascot size={46} className="mascot-bob" />}
        open={tour}
        onClose={close}
      />
      <GuideDock onTour={() => setTour(true)} />
    </>
  );
}

type Msg = { id: number; from: "me" | "mascot"; text: string; actions?: GuideAction[]; follow?: string[] };

function GuideDock({ onTour }: { onTour: () => void }) {
  const router = useRouter();
  const { toggle } = useTheme();
  const [open, setOpen] = useState(false);
  const [text, setText] = useState("");
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const seq = useRef(0);
  const log = useRef<HTMLDivElement>(null);
  const input = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    if (msgs.length === 0) {
      setMsgs([{ id: ++seq.current, from: "mascot", text: `Chào thầy cô, ${GUIDE_NAME} đây! Mình chỉ cách dùng PreClass AI: soạn bài từ nguồn, duyệt, giao bài và theo dõi lớp. Thầy cô cần gì?`, follow: [...START_CHIPS] }]);
    }
    input.current?.focus();
    const esc = (e: KeyboardEvent) => e.key === "Escape" && setOpen(false);
    document.addEventListener("keydown", esc);
    return () => document.removeEventListener("keydown", esc);
  }, [open]); // eslint-disable-line react-hooks/exhaustive-deps -- greet only when first opened

  useEffect(() => {
    if (log.current) log.current.scrollTop = log.current.scrollHeight;
  }, [msgs]);

  function reply(question: string, a: GuideAnswer) {
    setMsgs((x) => [...x, { id: ++seq.current, from: "me", text: question }, { id: ++seq.current, from: "mascot", text: a.text, actions: a.actions, follow: a.follow }]);
  }

  function act(a: GuideAction) {
    if (a.kind === "theme") return toggle();
    setOpen(false);
    if (a.kind === "tour") return onTour();
    if (a.kind === "go") return router.push(a.href);
    const box = document.getElementById(INSTALL_ANCHOR);
    if (box) box.scrollIntoView({ behavior: "smooth", block: "start" });
    else router.push(`/lessons#${INSTALL_ANCHOR}`);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const q = text.trim();
    if (!q) return;
    setText("");
    reply(q, answerGuide(q));
  }

  return (
    <div className="mascot-dock" style={{ ["--mascot" as string]: GUIDE_ACCENT }}>
      {open ? (
        <section className="mascot-panel" role="dialog" aria-label={`Hỏi ${GUIDE_NAME} cách dùng`}>
          <header className="mascot-panel-head">
            <GlobeMascot size={44} />
            <div>
              <strong>{GUIDE_NAME}</strong>
              <span className="muted small">Trợ lý hướng dẫn cho thầy cô</span>
            </div>
            <button type="button" className="habit-close" onClick={() => setOpen(false)} aria-label={`Đóng ${GUIDE_NAME}`}>
              ×
            </button>
          </header>
          <div ref={log} className="mascot-log" aria-live="polite">
            {msgs.map((m, idx) => (
              <div key={m.id} className={`mascot-msg ${m.from}`}>
                {m.from === "mascot" ? <GlobeMascot size={28} /> : null}
                <div className="mascot-bubble">
                  <p>{m.text}</p>
                  {m.actions?.length ? (
                    <div className="mascot-actions row-actions">
                      {m.actions.map((a) => (
                        <button key={a.label} type="button" className="btn btn-primary" onClick={() => act(a)}>
                          {a.label}
                        </button>
                      ))}
                    </div>
                  ) : null}
                  {m.follow?.length && idx === msgs.length - 1 ? (
                    <div className="mascot-chips" role="group" aria-label="Thầy cô có thể hỏi">
                      {m.follow.map((id) => (
                        <button key={id} type="button" className="habit-chip" onClick={() => reply(chipLabel(id), answerChip(id))}>
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
              placeholder="Ví dụ: nhắc học sinh chưa làm thế nào?"
              aria-label={`Câu hỏi cho ${GUIDE_NAME}`}
              autoComplete="off"
            />
            <button type="submit" className="btn btn-primary" disabled={!text.trim()}>
              Gửi
            </button>
          </form>
          <p className="mascot-note">{GUIDE_NAME} chỉ hướng dẫn cách dùng, câu trả lời có sẵn, không gửi gì ra ngoài.</p>
        </section>
      ) : null}
      <button
        type="button"
        className={`mascot-fab${open ? " on" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        aria-label={open ? `Thu gọn ${GUIDE_NAME}` : `Hỏi ${GUIDE_NAME}: hướng dẫn sử dụng`}
        data-tour="teacher-guide"
      >
        <GlobeMascot size={58} className="mascot-bob" />
        <span className="mascot-fab-name">{GUIDE_NAME}</span>
      </button>
    </div>
  );
}
