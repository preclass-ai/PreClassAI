"use client";

import { Field } from "@/components/ui";
import type { Block, BlockPayload } from "@/lib/blocks";
import { ITEM_TYPE, SKILL } from "@/lib/labels";

type Rec = Record<string, unknown>;

function s(p: Rec, k: string): string {
  const v = p[k];
  return typeof v === "string" ? v : "";
}

function n(p: Rec, k: string): string {
  const v = p[k];
  return typeof v === "number" ? String(v) : "";
}

/** Form fields for each block kind. Unknown keys of the original payload (e.g. `derivation`) are preserved. */
export function PayloadEditor({ kind, value, onChange }: {
  kind: Block["kind"];
  value: BlockPayload;
  onChange: (p: BlockPayload) => void;
}) {
  const p = value as Rec;
  const set = (k: string, v: unknown) => onChange({ ...p, [k]: v } as BlockPayload);
  const setNum = (k: string, raw: string) => set(k, raw.trim() === "" ? null : Number(raw.replace(",", ".")));

  switch (kind) {
    case "data_fact":
      return (
        <div className="stack">
          <Field label="Nhãn">
            <input required value={s(p, "label")} onChange={(e) => set("label", e.target.value)} />
          </Field>
          <div className="row">
            <Field label="Giá trị">
              <input required inputMode="decimal" value={n(p, "value")} onChange={(e) => setNum("value", e.target.value)} />
            </Field>
            <Field label="Đơn vị">
              <input required value={s(p, "unit")} onChange={(e) => set("unit", e.target.value)} />
            </Field>
          </div>
          <div className="row">
            <Field label="Vùng / địa điểm">
              <input required value={s(p, "region")} onChange={(e) => set("region", e.target.value)} />
            </Field>
            <Field label="Thời điểm">
              <input required value={s(p, "period")} onChange={(e) => set("period", e.target.value)} />
            </Field>
          </div>
          <Field label="Ghi chú">
            <input value={s(p, "note")} onChange={(e) => set("note", e.target.value || null)} />
          </Field>
        </div>
      );
    case "worksheet_item":
      return (
        <div className="stack">
          <div className="row">
            <Field label="Dạng câu">
              <select value={s(p, "itemType")} onChange={(e) => set("itemType", e.target.value)}>
                {Object.entries(ITEM_TYPE).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Kỹ năng">
              <select value={s(p, "skill")} onChange={(e) => set("skill", e.target.value)}>
                {Object.entries(SKILL).map(([k, v]) => (
                  <option key={k} value={k}>
                    {v}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          <Field label="Đề bài">
            <textarea required rows={3} value={s(p, "stem")} onChange={(e) => set("stem", e.target.value)} />
          </Field>
        </div>
      );
    case "option":
      return (
        <div className="row">
          <Field label="Nhãn">
            <select value={s(p, "label")} onChange={(e) => set("label", e.target.value)}>
              {["A", "B", "C", "D"].map((l) => (
                <option key={l}>{l}</option>
              ))}
            </select>
          </Field>
          <Field label="Nội dung phương án">
            <input required value={s(p, "text")} onChange={(e) => set("text", e.target.value)} />
          </Field>
        </div>
      );
    case "answer_key": {
      const rubric = Array.isArray(p.rubricPoints) ? (p.rubricPoints as unknown[]).map(String).join("\n") : "";
      return (
        <div className="stack">
          <div className="row">
            <Field label="Đáp án trắc nghiệm">
              <select value={s(p, "correct")} onChange={(e) => set("correct", e.target.value || null)}>
                <option value="">Chọn</option>
                {["A", "B", "C", "D"].map((l) => (
                  <option key={l}>{l}</option>
                ))}
              </select>
            </Field>
            <Field label="Đáp số">
              <input inputMode="decimal" value={n(p, "value")} onChange={(e) => setNum("value", e.target.value)} />
            </Field>
            <Field label="Đơn vị">
              <input value={s(p, "unit")} onChange={(e) => set("unit", e.target.value || null)} />
            </Field>
            <Field label="Sai số cho phép">
              <input inputMode="decimal" value={n(p, "tolerance")} onChange={(e) => setNum("tolerance", e.target.value)} />
            </Field>
          </div>
          <Field label="Ý chấm (mỗi dòng một ý, cho câu tự luận)">
            <textarea
              rows={3}
              value={rubric}
              onChange={(e) => {
                const lines = e.target.value.split("\n");
                set("rubricPoints", lines.some((l) => l.trim()) ? lines : null);
              }}
            />
          </Field>
        </div>
      );
    }
    default:
      return (
        <Field label="Nội dung">
          <textarea required rows={4} value={s(p, "text")} onChange={(e) => set("text", e.target.value)} />
        </Field>
      );
  }
}

/** Trim rubric lines before sending (empty lines are an editing artefact). */
export function cleanPayload(kind: Block["kind"], payload: BlockPayload): BlockPayload {
  if (kind !== "answer_key") return payload;
  const p = { ...(payload as Rec) };
  if (Array.isArray(p.rubricPoints)) {
    const pts = (p.rubricPoints as string[]).map((x) => x.trim()).filter(Boolean);
    p.rubricPoints = pts.length ? pts : null;
  }
  return p as BlockPayload;
}
