"use client";

import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { ErrorBox, Loading } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";

/**
 * "Tiến độ học sinh": how far each class got on what it was assigned, and who to remind.
 * Class-level numbers only (the page never names a student, same rule as Lớp & bài giao); the CSV per assignment lists
 * login codes for a teacher who needs to know exactly who.
 * Same query keys as the classes page, so opening an assignment there reuses these answers.
 */
type Assignment = Schemas["AssignmentOut"];
type Progress = Schemas["ProgressOut"];
type ClassInfo = Pick<Schemas["ClassOut"], "id" | "code">;

export type Phase = "soon" | "open" | "closed" | "upcoming";
const HOUR = 3_600_000;
const SOON_HOURS = 48;
const CLOSED_DAYS = 14; // closed assignments stay on the board this long
const ALERT_CLOSED_DAYS = 7;

export interface Row {
  cls: ClassInfo;
  a: Assignment;
  phase: Phase;
  done: number;
  doing: number;
  todo: number;
  students: number;
  loaded: boolean;
}

export function phaseOf(a: Pick<Assignment, "openAt" | "dueAt">, now: number): Phase {
  const open = Date.parse(a.openAt);
  const due = Date.parse(a.dueAt);
  if (open > now) return "upcoming";
  if (due < now) return "closed";
  return due - now <= SOON_HOURS * HOUR ? "soon" : "open";
}

/** Closed long ago and not yet open assignments leave the board. */
export function onBoard(a: Pick<Assignment, "openAt" | "dueAt">, now: number): boolean {
  const p = phaseOf(a, now);
  return p === "soon" || p === "open" || (p === "closed" && now - Date.parse(a.dueAt) <= CLOSED_DAYS * 24 * HOUR);
}

export function toRow(cls: ClassInfo, a: Assignment, p: Progress | undefined, now: number): Row {
  const counts = p && typeof p.completedCount === "number" && typeof p.inProgressCount === "number";
  const students = p?.studentCount ?? 0;
  const done = counts ? p.completedCount : 0;
  const doing = counts ? p.inProgressCount : 0;
  return { cls, a, phase: phaseOf(a, now), done, doing, todo: counts ? Math.max(0, students - done - doing) : 0, students, loaded: !!counts };
}

/** Needs a reminder: closing within 48 h, or closed in the last week, with someone not finished. */
export function needsAttention(r: Row, now: number): boolean {
  if (!r.loaded || r.done >= r.students) return false;
  if (r.phase === "soon") return true;
  return r.phase === "closed" && now - Date.parse(r.a.dueAt) <= ALERT_CLOSED_DAYS * 24 * HOUR;
}

const ORDER: Record<Phase, number> = { soon: 0, open: 1, closed: 2, upcoming: 3 };
export function sortRows(rows: Row[]): Row[] {
  return [...rows].sort((x, y) => {
    if (ORDER[x.phase] !== ORDER[y.phase]) return ORDER[x.phase] - ORDER[y.phase];
    const dx = Date.parse(x.a.dueAt);
    const dy = Date.parse(y.a.dueAt);
    return x.phase === "closed" ? dy - dx : dx - dy;
  });
}

export interface Summary {
  rate: number | null; // share of student-assignments finished, over the assignments still open (else all on the board)
  todo: number;
  doing: number;
  urgent: number; // assignments that need a reminder
  scope: "open" | "all";
}

export function summarize(rows: Row[], now: number): Summary {
  const loaded = rows.filter((r) => r.loaded);
  const active = loaded.filter((r) => r.phase === "soon" || r.phase === "open");
  const pool = active.length ? active : loaded;
  const total = pool.reduce((n, r) => n + r.students, 0);
  return {
    rate: total ? pool.reduce((n, r) => n + r.done, 0) / total : null,
    todo: pool.reduce((n, r) => n + r.todo, 0),
    doing: pool.reduce((n, r) => n + r.doing, 0),
    urgent: loaded.filter((r) => needsAttention(r, now)).length,
    scope: active.length ? "open" : "all",
  };
}

/** Text a teacher can paste into the class group chat. */
export function reminderText(r: Row): string {
  const left = r.todo + r.doing;
  const when = r.phase === "closed" ? `đã hết hạn lúc ${fmtDateTime(r.a.dueAt)}` : `hạn ${fmtDateTime(r.a.dueAt)}`;
  return `Lớp ${r.cls.code} ơi, bài “${r.a.studentTitle}” ${when}. Còn ${left} em chưa làm xong${r.doing ? ` (${r.doing} em đang làm dở)` : ""}. Các em vào PreClass AI làm trước giờ lên lớp nhé!`;
}

export function timeLeft(dueAt: string, now: number): string {
  const ms = Date.parse(dueAt) - now;
  const h = Math.round(Math.abs(ms) / HOUR);
  const span = h < 1 ? "dưới 1 giờ" : h < 48 ? `${h} giờ` : `${Math.round(h / 24)} ngày`;
  return ms >= 0 ? `còn ${span}` : `quá hạn ${span}`;
}

const pct = (n: number, d: number) => (d ? Math.round((100 * n) / d) : 0);

export function ClassProgressBoard({ classId, title = "Tiến độ học sinh" }: { classId?: string; title?: string }) {
  const qc = useQueryClient();
  const [now, setNow] = useState(() => Date.now());
  const [onlyAttention, setOnlyAttention] = useState(false);
  const [pick, setPick] = useState<string>("all");
  const classes = useQuery({ queryKey: ["classes"], queryFn: () => unwrap(api.GET("/v1/classes")) });
  const targets = useMemo(() => (classes.data?.items ?? []).filter((c) => !classId || c.id === classId), [classes.data, classId]);

  const lists = useQueries({
    queries: targets.map((c) => ({
      queryKey: ["class-assignments", c.id],
      queryFn: () => unwrap(api.GET("/v1/classes/{class_id}/assignments", { params: { path: { class_id: c.id } } })),
    })),
  });
  const pairs = targets.flatMap((c, i) => (lists[i]?.data?.items ?? []).filter((a) => onBoard(a, now)).map((a) => ({ c, a })));
  const progress = useQueries({
    queries: pairs.map(({ c, a }) => ({
      queryKey: ["progress", c.id, a.id],
      queryFn: () =>
        unwrap(api.GET("/v1/classes/{class_id}/assignments/{assignment_id}/progress", { params: { path: { class_id: c.id, assignment_id: a.id } } })),
    })),
  });

  const rows = sortRows(pairs.map(({ c, a }, i) => toRow(c, a, progress[i]?.data, now)));
  const inClass = rows.filter((r) => pick === "all" || r.cls.id === pick);
  const alerts = inClass.filter((r) => needsAttention(r, now));
  const shown = onlyAttention ? alerts : inClass;
  const summary = summarize(inClass, now);
  const error = classes.error ?? lists.find((l) => l.error)?.error ?? progress.find((p) => p.error)?.error ?? null;
  const pending = classes.isPending || lists.some((l) => l.isPending);

  async function refresh() {
    setNow(Date.now());
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["class-assignments"] }),
      qc.invalidateQueries({ queryKey: ["progress"] }),
    ]);
  }

  const pctAll = summary.rate === null ? null : Math.round(summary.rate * 100);
  const classLabel = targets.find((c) => c.id === pick)?.code;

  return (
    <section className="card pb" aria-labelledby="pb-title" data-tour="progress">
      <header className="pb-head">
        <div>
          <h2 id="pb-title">{title}</h2>
          <p className="muted small">Số liệu cả lớp, không hiện tên. Cần biết từng em thì tải danh sách CSV (theo mã đăng nhập).</p>
        </div>
        <div className="pb-tools">
          {!classId && targets.length > 1 ? (
            <div className="pb-seg-ctl" role="group" aria-label="Lớp">
              <button type="button" aria-pressed={pick === "all"} onClick={() => setPick("all")}>Tất cả lớp</button>
              {targets.map((c) => (
                <button key={c.id} type="button" aria-pressed={pick === c.id} onClick={() => setPick(c.id)}>{c.code}</button>
              ))}
            </div>
          ) : null}
          <label className="pb-switch">
            <input type="checkbox" checked={onlyAttention} onChange={(e) => setOnlyAttention(e.target.checked)} />
            <span aria-hidden="true" />
            Chỉ bài cần nhắc
          </label>
          <button type="button" className="pb-icon-btn" onClick={() => void refresh()} aria-label="Cập nhật số liệu" title="Cập nhật số liệu">
            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M20 11a8 8 0 1 0-2.3 5.7" /><path d="M20 4v7h-7" />
            </svg>
          </button>
        </div>
      </header>
      <ErrorBox error={error} />
      {pending ? (
        <Loading />
      ) : rows.length === 0 ? (
        <p className="pb-empty">Chưa có bài nào đang mở. Giao bài cho lớp là tiến độ hiện ở đây.</p>
      ) : (
        <>
          <dl className="pb-kpis">
            <div className="pb-kpi">
              <dt>Hoàn thành</dt>
              <dd>
                <strong>{pctAll === null ? "–" : `${pctAll}%`}</strong>
                <span className="pb-meter" aria-hidden="true"><span style={{ width: `${pctAll ?? 0}%` }} /></span>
              </dd>
              <small>{summary.scope === "open" ? "trên các bài đang mở" : "trên các bài gần đây"}{classLabel ? ` · ${classLabel}` : ""}</small>
            </div>
            <div className={`pb-kpi${summary.todo ? " is-danger" : ""}`}>
              <dt>Chưa mở bài</dt>
              <dd><strong>{summary.todo}</strong></dd>
              <small>lượt học sinh</small>
            </div>
            <div className="pb-kpi">
              <dt>Đang làm dở</dt>
              <dd><strong>{summary.doing}</strong></dd>
              <small>lượt học sinh</small>
            </div>
            <div className={`pb-kpi${summary.urgent ? " is-warning" : ""}`}>
              <dt>Cần nhắc</dt>
              <dd><strong>{summary.urgent}</strong></dd>
              <small>{summary.urgent ? "bài sắp hoặc vừa hết hạn" : "không có bài nào"}</small>
            </div>
          </dl>

          {alerts.length ? <Alerts rows={alerts} now={now} /> : null}

          {shown.length === 0 ? (
            <p className="pb-empty">Không có bài nào cần nhắc. Lớp đang theo kịp.</p>
          ) : (
            <div className="pb-table">
              <div className="pb-thead" aria-hidden="true">
                <span>Bài</span>
                <span>Hạn nộp</span>
                <span className="pb-legend">
                  Tiến độ
                  <i className="pb-dot done" /> Xong
                  <i className="pb-dot doing" /> Đang làm
                  <i className="pb-dot todo" /> Chưa làm
                </span>
                <span className="pb-right">Xong</span>
              </div>
              <ul className="pb-rows plain">
                {shown.map((r) => (
                  <ProgressRow key={r.a.id} r={r} now={now} attention={needsAttention(r, now)} />
                ))}
              </ul>
            </div>
          )}
        </>
      )}
    </section>
  );
}

function ProgressRow({ r, now, attention }: { r: Row; now: number; attention: boolean }) {
  const href = `/classes?class=${r.cls.id}&assignment=${r.a.id}`;
  const left = timeLeft(r.a.dueAt, now);
  const tone = r.phase === "closed" ? "closed" : r.phase === "soon" ? "soon" : "open";
  const w = (n: number) => `${r.students ? (100 * n) / r.students : 0}%`;
  return (
    <li className={`pb-row${attention ? " attention" : ""}`}>
      <div className="pb-label">
        <Link href={href}>{r.a.studentTitle}</Link>
        <span className="muted small">
          Lớp {r.cls.code}
          {attention ? <span className="pb-flag">Cần nhắc</span> : null}
        </span>
      </div>
      <div className={`pb-due ${tone}`}>
        <span>{left.charAt(0).toUpperCase() + left.slice(1)}</span>
        <small className="muted">{fmtDateTime(r.a.dueAt)}</small>
      </div>
      {!r.loaded ? (
        <span className="pb-track pb-wait" aria-label="Đang tải tiến độ" />
      ) : r.students === 0 ? (
        <span className="muted small">Lớp chưa có học sinh</span>
      ) : (
        <div className="pb-progress">
          <span
            className="pb-track"
            role="img"
            aria-label={`${r.a.studentTitle}, lớp ${r.cls.code}: ${r.done} em đã xong, ${r.doing} em đang làm, ${r.todo} em chưa làm, trên ${r.students} em`}
          >
            {r.done ? <span className="pb-fill done" style={{ width: w(r.done) }} title={`Đã xong: ${r.done} em`} /> : null}
            {r.doing ? <span className="pb-fill doing" style={{ width: w(r.doing) }} title={`Đang làm: ${r.doing} em`} /> : null}
          </span>
          <span className="pb-counts small">
            <b>{r.done}</b> xong · <b>{r.doing}</b> đang làm · <b className={r.todo ? "todo" : undefined}>{r.todo}</b> chưa làm
          </span>
        </div>
      )}
      <div className="pb-pct">
        <strong>{r.loaded ? `${pct(r.done, r.students)}%` : "…"}</strong>
        <small>{r.loaded ? `${r.done}/${r.students}` : ""}</small>
      </div>
    </li>
  );
}

function Alerts({ rows, now }: { rows: Row[]; now: number }) {
  const [copied, setCopied] = useState<string | null>(null);
  async function copy(r: Row) {
    try {
      await navigator.clipboard.writeText(reminderText(r));
      setCopied(r.a.id);
    } catch {
      window.prompt("Sao chép lời nhắc này:", reminderText(r));
    }
  }
  return (
    <div className="pb-alerts" role="region" aria-label="Cần nhắc học sinh">
      <h3>
        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
          <path d="M12 8v5M12 16.5v.5" /><path d="M10.3 3.9 2.6 17.2A2 2 0 0 0 4.3 20h15.4a2 2 0 0 0 1.7-2.8L13.7 3.9a2 2 0 0 0-3.4 0z" />
        </svg>
        Cần nhắc ngay <span className="muted">· {rows.length} bài</span>
      </h3>
      <ul className="plain">
        {rows.map((r) => (
          <li key={r.a.id}>
            <div>
              <strong>{r.cls.code} · {r.a.studentTitle}</strong>
              <span>
                <b>{r.todo}</b> em chưa làm{r.doing ? <>, <b>{r.doing}</b> em làm dở</> : null} · {timeLeft(r.a.dueAt, now)}
              </span>
            </div>
            <div className="row-actions">
              <button type="button" className="btn pb-btn" onClick={() => void copy(r)}>
                {copied === r.a.id ? "Đã sao chép ✓" : "Sao chép lời nhắc"}
              </button>
              <a className="link-btn" href={`/v1/classes/${r.cls.id}/assignments/${r.a.id}/results.csv`} download>
                Danh sách (CSV)
              </a>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
