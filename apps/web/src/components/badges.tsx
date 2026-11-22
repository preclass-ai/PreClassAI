import type { Block } from "@/lib/blocks";
import { REVIEW_STATUS, REVISION_STATE, TRANSFORMATION, type RevisionState } from "@/lib/labels";
import { Badge } from "./ui";

export function ReviewBadge({ status }: { status: Block["reviewStatus"] }) {
  const s = REVIEW_STATUS[status];
  // Machine-checked is outlined violet with a gear, approved is filled green with a tick: "checked" never reads as "approved".
  return status === "AUTO_CHECKED" ? <Badge tone="neutral" className="badge-machine">{s.label}</Badge> : <Badge tone={s.tone}>{s.label}</Badge>;
}

export function StateBadge({ state }: { state: RevisionState }) {
  const s = REVISION_STATE[state];
  return <Badge tone={s.tone}>{s.label}</Badge>;
}

/**
 * Source evidence, shown SEPARATELY from review status: having a source does not mean the block is correct.
 */
export function SourceBadge({ block }: { block: Pick<Block, "linkCount" | "transformation" | "noSourceReason"> & Partial<Pick<Block, "remediationDraft" | "reviewStatus">> }) {
  const n = block.linkCount ?? 0;
  const label = TRANSFORMATION[block.transformation];
  const redo = block.remediationDraft && block.reviewStatus !== "APPROVED" ? <Badge tone="info">Bản nháp dạy lại</Badge> : null;
  if (n === 0) {
    return (
      <>
        {redo}
        <Badge tone={block.noSourceReason ? "neutral" : "warning"} title={block.noSourceReason ?? undefined}>
          Không có nguồn · {label}
        </Badge>
      </>
    );
  }
  return (
    <>
      {redo}
      <Badge tone="neutral">
        {n} đoạn nguồn · {label}
      </Badge>
    </>
  );
}

export function IssueCounts({ block }: { block: Pick<Block, "blockerCount" | "warningCount"> }) {
  const b = block.blockerCount ?? 0;
  const w = block.warningCount ?? 0;
  if (!b && !w) return null;
  return (
    <>
      {b ? <Badge tone="danger">{b} lỗi chặn</Badge> : null}
      {w ? <Badge tone="warning">{w} cảnh báo</Badge> : null}
    </>
  );
}
