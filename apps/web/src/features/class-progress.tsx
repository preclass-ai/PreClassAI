"use client";

import { useQueries, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useMemo, useState } from "react";
import { Badge, ErrorBox, Loading } from "@/components/ui";
import { api, unwrap, type Schemas } from "@/lib/api";
import { fmtDateTime } from "@/lib/format";
import type { Tone } from "@/lib/labels";

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

const PHASE: Record<Phase, { label: string; tone: Tone }> = {
  soon: { label: "Sắp hết hạn", tone: "warning" },
  open: { label: "Đang mở", tone: "info" },
  closed: { label: "Đã hết hạn", tone: "neutral" },
  upcoming: { label: "Chưa mở", tone: "neutral" },
};

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

  return (
    <section className="card pb" aria-labelledby="pb-title" data-tour="progress">
      <div className="section-head">
        <div>
          <h2 id="pb-title">{title}</h2>
          <p className="muted small">
            Số liệu của cả lớp, không hiện tên. Cần biết cụ thể em nào thì tải tệp kết quả (theo mã đăng nhập).
          </p>
        </div>
        <button type="button" className="btn" onClick={() => void refresh()}>Cập nhật</button>
      </div>
      <ErrorBox error={error} />
      {pending ? (
        <Loading />
      ) : rows.length === 0 ? (
        <p className="pb-empty">Chưa có bài nào đang mở. Giao bài cho lớp là tiến độ hiện ở đây.</p>
      ) : (
        <>
          <div className="pb-filters">
            {!classId && targets.length > 1 ? (
              <label>
                Lớp{" "}
                <select value={pick} onChange={(e) => setPick(e.target.value)}>
                  <option value="all">Tất cả lớp</option>
                  {targets.map((c) => (
                    <option key={c.id} value={c.id}>{c.code}</option>
                  ))}
                </select>
              </label>
            ) : null}
            <label className="pb-check">
              <input type="checkbox" checked={onlyAttention} onChange={(e) => setOnlyAttention(e.target.checked)} /> Chỉ bài cần nhắc
            </label>
          </div>

          <div className="pb-tiles">
            <div className="pb-tile pb-tile-hero">
              <span>Đã hoàn thành</span>
              <strong>{summary.rate === null ? "–" : `${Math.round(summary.rate * 100)}%`}</strong>
              <small>{summary.scope === "open" ? "lượt bài đang mở" : "lượt bài trên bảng"}</small>
            </div>
            <div className={`pb-tile${summary.todo ? " pb-tile-alert" : ""}`}>
              <span><i aria-hidden="true">○</i> Chưa làm</span>
              <strong>{summary.todo}</strong>
              <small>lượt học sinh chưa mở bài</small>
            </div>
            <div className="pb-tile">
              <span><i aria-hidden="true">◐</i> Đang làm dở</span>
              <strong>{summary.doing}</strong>
              <small>đã làm một phần</small>
            </div>
            <div className={`pb-tile${summary.urgent ? " pb-tile-warn" : ""}`}>
              <span><i aria-hidden="true">⏰</i> Cần nhắc</span>
              <strong>{summary.urgent}</strong>
              <small>bài sắp hoặc vừa hết hạn còn em chưa xong</small>
            </div>
          </div>

          {alerts.length ? <Alerts rows={alerts} now={now} /> : null}

          <div className="pb-legend" aria-hidden="true">
            <span><i className="pb-sw done" /> ✓ Đã xong</span>
            <span><i className="pb-sw doing" /> ◐ Đang làm</span>
            <span><i className="pb-sw todo" /> ○ Chưa làm</span>
          </div>
          {shown.length === 0 ? (
            <p className="pb-empty">Không có bài nào cần nhắc. Lớp đang theo kịp!</p>
          ) : (
            <ul className="pb-rows plain">
              {shown.map((r) => (
                <ProgressRow key={r.a.id} r={r} now={now} attention={needsAttention(r, now)} />
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  );
}

function Segment({ kind, n, of, label }: { kind: "done" | "doing" | "todo"; n: number; of: number; label: string }) {
  if (!n) return null;
  const share = pct(n, of);
  return (
    <span className={`pb-seg ${kind}`} style={{ width: `${(100 * n) / of}%` }} data-tip={`${label}: ${n} em (${share}%)`}>
      {share >= 9 ? n : ""}
    </span>
  );
}

function ProgressRow({ r, now, attention }: { r: Row; now: number; attention: boolean }) {
  const phase = PHASE[r.phase];
  const href = `/classes?class=${r.cls.id}&assignment=${r.a.id}`;
  return (
    <li className={`pb-row${attention ? " attention" : ""}`}>
      <div className="pb-label">
        <Link href={href}>{r.a.studentTitle}</Link>
        <span className="muted small">
          {r.cls.code} · hạn {fmtDateTime(r.a.dueAt)} · {timeLeft(r.a.dueAt, now)}
        </span>
      </div>
      <Badge tone={phase.tone}>{phase.label}</Badge>
      {!r.loaded ? (
        <span className="pb-bar pb-bar-wait" aria-label="Đang tải tiến độ" />
      ) : r.students === 0 ? (
        <span className="muted small pb-bar-none">Lớp chưa có học sinh</span>
      ) : (
        <span
          className="pb-bar"
          role="img"
          aria-label={`${r.a.studentTitle}, lớp ${r.cls.code}: ${r.done} em đã xong, ${r.doing} em đang làm, ${r.todo} em chưa làm, trên ${r.students} em`}
        >
          <Segment kind="done" n={r.done} of={r.students} label="Đã xong" />
          <Segment kind="doing" n={r.doing} of={r.students} label="Đang làm" />
          <Segment kind="todo" n={r.todo} of={r.students} label="Chưa làm" />
        </span>
      )}
      <span className="pb-pct">
        <strong>{r.loaded ? `${pct(r.done, r.students)}%` : "…"}</strong>
        <small>{r.loaded ? `${r.done}/${r.students} xong` : ""}</small>
      </span>
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
      <h3><span aria-hidden="true">⚠</span> Cần nhắc ngay</h3>
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
              <button type="button" className="btn" onClick={() => void copy(r)}>
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
