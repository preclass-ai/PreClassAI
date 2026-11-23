"use client";

import { useEffect, useRef } from "react";
import { fmtDate } from "@/lib/format";
import { LAST_STAGE, SPECIES, stageFor, stageProgress, stageRange, tasksToNext } from "./species";
import { openSeedPicker, startTour, useGarden, useProgress } from "./store";
import { TreeSprite } from "./tree";

/** Student home: the tree grown by finished assignments, the assignment streak, and the seven-stage journey. */
export function GardenCard() {
  const { ready, species } = useGarden();
  const progress = useProgress();
  const journey = useRef<HTMLOListElement>(null);
  const stage = stageFor(progress?.done ?? 0);
  useEffect(() => {
    // Narrow screens scroll the stages sideways: bring the current one into view (without moving the page).
    const ol = journey.current;
    const li = ol?.querySelector<HTMLElement>('[aria-current="step"]');
    if (ol && li) ol.scrollLeft = li.offsetLeft - (ol.clientWidth - li.offsetWidth) / 2;
  }, [stage, species]);
  if (!ready) return null;

  if (!species) {
    return (
      <section className="card garden garden-empty" aria-label="Khu vườn tri thức" data-tour="garden">
        <div className="garden-empty-seeds" aria-hidden="true">
          {SPECIES.map((s) => (
            <TreeSprite key={s.id} species={s} stage={0} size={44} alt="" />
          ))}
        </div>
        <div>
          <h2>Khu vườn tri thức</h2>
          <p className="muted">Chọn một hạt giống: mỗi bài em làm xong, cây lớn thêm, và cây sẽ là người đồng hành hướng dẫn em.</p>
        </div>
        <button type="button" className="btn btn-primary" onClick={openSeedPicker}>
          Chọn hạt giống
        </button>
      </section>
    );
  }

  const done = progress?.done ?? 0;
  const left = tasksToNext(done);
  const next = progress?.pending[0];
  const allDone = !!progress && progress.pending.length === 0 && done > 0;

  return (
    <section className="card garden" aria-label={`Khu vườn: ${species.name}`} style={{ ["--mascot" as string]: species.accent }} data-tour="garden">
      <div className="garden-main">
        <div className={`garden-stage${stage === LAST_STAGE ? " max" : ""}`}>
          <TreeSprite species={species} stage={stage} size={200} priority className="garden-tree" />
          {allDone ? <span className="garden-spark" aria-hidden="true">✦</span> : null}
        </div>
        <div className="garden-info">
          <p className="eyebrow">{species.name} của em</p>
          <h2 className="garden-title">{species.stages[stage]}</h2>
          {progress ? (
            <>
              <p className="garden-streak">
                <span aria-hidden="true">🔥</span> <strong>{progress.streak}</strong> bài liên tiếp
                <span className="muted small"> · đã xong {done} bài</span>
              </p>
              <div className="garden-goal">
                <span className="small">{left !== null ? `Còn ${left} bài nữa là tới “${species.stages[stage + 1]}”` : "Cây đã lớn hết cỡ"}</span>
                <span className="bar" role="progressbar" aria-label="Tới giai đoạn tiếp theo" aria-valuemin={0} aria-valuemax={100} aria-valuenow={Math.round(100 * stageProgress(done))}>
                  <span style={{ width: `${100 * stageProgress(done)}%` }} />
                </span>
              </div>
              <p className="garden-say bubble">
                <strong>{species.mascot}:</strong>{" "}
                {next
                  ? `${species.nudge} Bài “${next.title}” hạn ${fmtDate(next.dueAt)}, xong trước hạn là giữ được chuỗi.`
                  : allDone
                    ? `${species.cheer} Không có bài nào đang chờ, nghỉ ngơi thoải mái nhé.`
                    : "Khi thầy cô giao bài, em làm xong bài nào là mình lớn thêm bài đó."}
              </p>
            </>
          ) : null}
          <div className="row-actions">
            <button type="button" className="btn btn-ghost" onClick={openSeedPicker}>
              Đổi giống cây
            </button>
            <button type="button" className="btn btn-ghost" onClick={startTour}>
              Xem hướng dẫn
            </button>
          </div>
        </div>
      </div>
      <ol ref={journey} className="garden-journey" aria-label="Các giai đoạn phát triển">
        {species.stages.map((name, i) => (
          <li key={name} className={i < stage ? "past" : i === stage ? "now" : "next"} aria-current={i === stage ? "step" : undefined}>
            <TreeSprite species={species} stage={i} size={64} alt="" />
            <span className="garden-journey-days">{stageRange(i)}</span>
            <span className="garden-journey-name">{name}</span>
          </li>
        ))}
      </ol>
    </section>
  );
}
