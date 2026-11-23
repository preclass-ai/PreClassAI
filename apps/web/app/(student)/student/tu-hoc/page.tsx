"use client";

import Link from "next/link";
import { useEffect, useRef, useState, useSyncExternalStore } from "react";
import { MascotAvatar } from "@/features/garden/tree";
import { stageFor } from "@/features/garden/species";
import { useMascot, useProgress } from "@/features/garden/store";
import type { Species } from "@/features/garden/species";
import { MethodCoach } from "@/features/self-study/coach";
import { GROUPS, METHOD_BY_ID, METHODS, PROBLEMS, type Group, type Method } from "@/features/self-study/methods";

/** "Tự học": pick a way to study before class. Ticks are kept in this browser only. */
const KEY = "preclass.selfstudy";
const EVENT = "preclass-selfstudy";

type Ticks = Record<string, number[]>;
function readTicks(): string {
  try {
    return localStorage.getItem(KEY) ?? "{}";
  } catch {
    return "{}";
  }
}
function parseTicks(raw: string): Ticks {
  try {
    const v = JSON.parse(raw) as unknown;
    return v && typeof v === "object" ? (v as Ticks) : {};
  } catch {
    return {};
  }
}
function subscribe(cb: () => void) {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}
function useTicks(): [Ticks, (id: string, step: number, value: boolean) => void] {
  const raw = useSyncExternalStore(subscribe, readTicks, () => "{}");
  const ticks = parseTicks(raw);
  function set(id: string, step: number, value: boolean) {
    const cur = parseTicks(readTicks());
    const list = new Set(cur[id] ?? []);
    if (value) list.add(step);
    else list.delete(step);
    try {
      localStorage.setItem(KEY, JSON.stringify({ ...cur, [id]: [...list] }));
    } catch {
      /* blocked: ticks last for this page */
    }
    window.dispatchEvent(new Event(EVENT));
  }
  return [ticks, set];
}

export default function SelfStudyPage() {
  const mascot = useMascot();
  const stage = stageFor(useProgress()?.done ?? 0); // the mascot looks the same as in the garden
  const [problem, setProblem] = useState<string | null>(null);
  const [group, setGroup] = useState<Group | "all">("all");
  const [ticks, setTick] = useTicks();
  const [coach, setCoach] = useState<Method | null>(null);
  const guide = mascot?.mascot ?? "PreClass";
  const picks = problem ? (PROBLEMS.find((p) => p.id === problem)?.methods ?? []) : [];
  const list = METHODS.filter((m) => group === "all" || m.group === group);
  const tried = METHODS.filter((m) => (ticks[m.id]?.length ?? 0) >= m.steps.length).length;

  return (
    <div className="student-home stack self-study">
      <header className="ss-hero">
        <div>
          <p className="eyebrow">Kĩ năng tự học</p>
          <h1>Học trước thế nào cho hiểu sâu?</h1>
          <p>Mười lăm phút trước giờ lên lớp, đúng cách, là đủ để vào tiết tự tin. Chọn một cách hợp với em, làm theo từng bước và đánh dấu khi xong.</p>
        </div>
        <div className="ss-tried" aria-label={`Em đã thử trọn ${tried} trên ${METHODS.length} cách học`}>
          <strong>{tried}/{METHODS.length}</strong>
          <span>cách học đã thử trọn</span>
        </div>
      </header>

      <section className="card ss-pick" aria-labelledby="ss-pick-title">
        <div className="ss-pick-head">
          {mascot ? <MascotAvatar species={mascot} stage={stage} size={44} /> : <span className="ss-pick-icon" aria-hidden="true">💡</span>}
          <div>
            <h2 id="ss-pick-title">{mascot ? `${mascot.mascot} hỏi nè: em hay gặp khó gì nhất?` : "Em hay gặp khó gì nhất?"}</h2>
            <p className="muted small">Chọn một ý, mình gợi ý cách học hợp nhất.</p>
          </div>
        </div>
        <div className="ss-chips" role="group" aria-label="Khó khăn khi tự học">
          {PROBLEMS.map((p) => (
            <button key={p.id} type="button" className={`habit-chip${problem === p.id ? " on" : ""}`} aria-pressed={problem === p.id} onClick={() => setProblem(problem === p.id ? null : p.id)}>
              {p.label}
            </button>
          ))}
        </div>
        {picks.length ? (
          <div className="ss-recommend" aria-live="polite">
            <strong>Gợi ý cho em:</strong>
            {picks.map((id) => {
              const m = METHOD_BY_ID.get(id);
              return m ? (
                <button key={id} type="button" className="ss-rec" onClick={() => setCoach(m)}>
                  Học {m.name} cùng {guide} <span className="muted small">· {m.minutes}</span>
                </button>
              ) : null;
            })}
          </div>
        ) : null}
      </section>

      <section className="ss-plan card" aria-labelledby="ss-plan-title">
        <h2 id="ss-plan-title">Kế hoạch 15 phút trước giờ học</h2>
        <ol className="ss-plan-steps">
          <li><b>3 phút</b> Lướt tên bài, đề mục, bảng, biểu đồ (SQ3R · Survey).</li>
          <li><b>2 phút</b> Ghi 2 câu hỏi em muốn biết (KWL · Want).</li>
          <li><b>8 phút</b> Làm bài được giao, kẹt thì xin gợi ý từng bậc.</li>
          <li><b>2 phút</b> Gấp lại, tự nói 3 ý chính (Tự kiểm tra).</li>
        </ol>
        <Link className="btn btn-primary" href="/student">Mở bài được giao</Link>
      </section>

      <div className="ss-filter" role="tablist" aria-label="Nhóm cách học">
        <button type="button" role="tab" aria-selected={group === "all"} onClick={() => setGroup("all")}>Tất cả</button>
        {(Object.keys(GROUPS) as Group[]).map((g) => (
          <button key={g} type="button" role="tab" aria-selected={group === g} onClick={() => setGroup(g)}>
            {GROUPS[g].label} <span className="muted small">{GROUPS[g].hint}</span>
          </button>
        ))}
      </div>

      <ul className="ss-grid plain">
        {list.map((m) => (
          <MethodCard key={m.id} m={m} done={ticks[m.id] ?? []} onTick={(i, v) => setTick(m.id, i, v)} highlight={picks.includes(m.id)} species={mascot} stage={stage} onCoach={() => setCoach(m)} />
        ))}
      </ul>
      <p className="muted small">Lựa chọn và dấu tích chỉ lưu trên máy này, không gửi cho ai.</p>
      {coach ? (
        <MethodCoach
          method={coach}
          species={mascot}
          stage={stage}
          done={ticks[coach.id] ?? []}
          onTick={(i, v) => setTick(coach.id, i, v)}
          onClose={() => setCoach(null)}
          extra={(i) => (coach.timer && i === 1 ? <FocusTimer /> : null)}
        />
      ) : null}
    </div>
  );
}

function MethodCard({ m, done, onTick, highlight, species, stage, onCoach }: {
  m: Method;
  done: number[];
  onTick: (i: number, value: boolean) => void;
  highlight: boolean;
  species: Species | null;
  stage: number;
  onCoach: () => void;
}) {
  const [open, setOpen] = useState(highlight);
  useEffect(() => {
    if (highlight) setOpen(true);
  }, [highlight]);
  const count = done.filter((i) => i < m.steps.length).length;
  return (
    <li id={`m-${m.id}`} className={`card ss-card ss-${m.group}${highlight ? " picked" : ""}`}>
      <div className="ss-card-top">
        <span className="ss-tag">{GROUPS[m.group].label}</span>
        <span className="muted small">{m.minutes}</span>
      </div>
      <h3>{m.name}</h3>
      <p className="ss-short">{m.short}</p>
      <p className="small">{m.why}</p>
      <div className="ss-progress" aria-hidden="true"><span style={{ width: `${(100 * count) / m.steps.length}%` }} /></div>
      <div className="ss-actions">
        <button type="button" className="btn btn-primary ss-coach-btn" onClick={onCoach}>
          {species ? <MascotAvatar species={species} stage={stage} size={24} /> : null}
          {count >= m.steps.length ? "Học lại" : count ? "Học tiếp" : "Học"} cùng {species?.mascot ?? "PreClass"}
        </button>
        <button type="button" className="link-btn ss-toggle" aria-expanded={open} onClick={() => setOpen(!open)}>
          {open ? "Thu gọn" : `Xem ${m.steps.length} bước${count ? ` (${count} xong)` : ""}`}
        </button>
      </div>
      {open ? (
        <>
          <ol className="ss-steps plain">
            {m.steps.map((s, i) => (
              <li key={s.title}>
                <label>
                  <input type="checkbox" checked={done.includes(i)} onChange={(e) => onTick(i, e.target.checked)} />
                  <span><b>{s.title}</b> {s.text}</span>
                </label>
              </li>
            ))}
          </ol>
          <p className="ss-geo small"><span aria-hidden="true">🗺️</span> {m.geo}</p>
          {m.timer ? <FocusTimer /> : null}
          <p className="muted small">Nguồn: {m.origin}</p>
        </>
      ) : null}
    </li>
  );
}

const FOCUS = 25 * 60;
const BREAK = 5 * 60;

/** 25/5 timer; keeps counting from a start time, so a tab in the background stays right. */
function FocusTimer() {
  const [mode, setMode] = useState<"focus" | "break">("focus");
  const [endAt, setEndAt] = useState<number | null>(null);
  const [left, setLeft] = useState(FOCUS);
  const tick = useRef<number | null>(null);

  useEffect(() => {
    if (endAt === null) return;
    const run = () => {
      const s = Math.max(0, Math.round((endAt - Date.now()) / 1000));
      setLeft(s);
      if (s === 0) {
        const next = mode === "focus" ? "break" : "focus";
        setMode(next);
        setEndAt(null);
        setLeft(next === "focus" ? FOCUS : BREAK);
      }
    };
    run();
    tick.current = window.setInterval(run, 500);
    return () => {
      if (tick.current) window.clearInterval(tick.current);
    };
  }, [endAt, mode]);

  const mm = String(Math.floor(left / 60)).padStart(2, "0");
  const ss = String(left % 60).padStart(2, "0");
  return (
    <div className={`ss-timer ${mode}`}>
      <span className="ss-timer-label">{mode === "focus" ? "Tập trung" : "Nghỉ"}</span>
      <span className="ss-timer-time" role="timer" aria-live="off">{mm}:{ss}</span>
      <div className="row-actions">
        {endAt === null ? (
          <button type="button" className="btn btn-primary" onClick={() => setEndAt(Date.now() + left * 1000)}>Bắt đầu</button>
        ) : (
          <button type="button" className="btn" onClick={() => setEndAt(null)}>Tạm dừng</button>
        )}
        <button type="button" className="link-btn" onClick={() => { setEndAt(null); setMode("focus"); setLeft(FOCUS); }}>Đặt lại</button>
      </div>
    </div>
  );
}
