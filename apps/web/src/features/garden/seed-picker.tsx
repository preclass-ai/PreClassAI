"use client";

import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui";
import { LAST_STAGE, SPECIES, SPECIES_BY_ID, type SpeciesId } from "./species";
import { TreeSprite } from "./tree";

/**
 * "Chọn hạt giống": six seeds, each a future tree and a mascot with its own voice.
 * Modal <dialog>: focus stays inside, Esc closes (the first time it means "để sau").
 */
export function SeedPicker({ open, current, onChoose, onClose }: {
  open: boolean;
  current: SpeciesId | null;
  onChoose: (id: SpeciesId) => void;
  onClose: () => void;
}) {
  const dlg = useRef<HTMLDialogElement>(null);
  const [pick, setPick] = useState<SpeciesId>(current ?? "knowledge");
  const first = current === null;

  useEffect(() => {
    const d = dlg.current;
    if (!d) return;
    if (open && !d.open) {
      setPick(current ?? "knowledge");
      if (typeof d.showModal === "function") d.showModal();
      else d.setAttribute("open", "");
    }
    if (!open && d.open) {
      if (typeof d.close === "function") d.close();
      else d.removeAttribute("open");
    }
  }, [open, current]);

  const sp = SPECIES_BY_ID[pick];

  return (
    <dialog ref={dlg} className="seed-picker" aria-labelledby="seed-picker-title" onClose={onClose} style={{ ["--mascot" as string]: sp.accent }}>
      <header className="seed-picker-head">
        <div>
          <p className="eyebrow">{first ? "Bắt đầu hành trình" : "Khu vườn của em"}</p>
          <h2 id="seed-picker-title">{first ? "Chọn một hạt giống để gieo" : "Đổi giống cây"}</h2>
          <p className="muted">
            {first
              ? "Hạt giống em chọn sẽ lớn lên theo số bài em làm xong, và cũng là người đồng hành hướng dẫn em dùng PreClass."
              : "Số bài em đã làm xong vẫn giữ nguyên, cây mới sẽ ở đúng giai đoạn tương ứng."}
          </p>
        </div>
        <button type="button" className="seed-picker-close" onClick={onClose} aria-label={first ? "Để sau" : "Đóng"}>
          ×
        </button>
      </header>
      <div className="seed-grid" role="radiogroup" aria-label="Giống cây">
        {SPECIES.map((s) => (
          <button
            key={s.id}
            type="button"
            role="radio"
            aria-checked={pick === s.id}
            className={`seed-card${pick === s.id ? " on" : ""}`}
            style={{ ["--mascot" as string]: s.accent }}
            onClick={() => setPick(s.id)}
          >
            <span className="seed-card-art">
              <TreeSprite species={s} stage={LAST_STAGE} size={120} alt="" />
              <span className="seed-card-seed"><TreeSprite species={s} stage={0} size={40} alt="" /></span>
            </span>
            <strong>{s.name}</strong>
            <span className="seed-card-trait">{s.trait}</span>
          </button>
        ))}
      </div>
      <div className="seed-preview" aria-live="polite">
        <TreeSprite species={sp} stage={1} size={64} alt="" className="mascot-bob" />
        <p className="bubble">
          <strong>{sp.mascot}:</strong> {sp.hello}
        </p>
      </div>
      <footer className="seed-picker-foot">
        {first ? (
          <button type="button" className="link-btn" onClick={onClose}>
            Để sau
          </button>
        ) : null}
        <Button variant="primary" onClick={() => onChoose(pick)} disabled={!first && pick === current}>
          {first ? `Gieo hạt ${sp.name.toLowerCase()}` : `Đổi sang ${sp.name.toLowerCase()}`}
        </Button>
      </footer>
    </dialog>
  );
}
