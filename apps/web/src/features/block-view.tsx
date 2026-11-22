import { summarize, type Block } from "@/lib/blocks";
import { ITEM_TYPE, KIND, SKILL } from "@/lib/labels";
import { IssueCounts, ReviewBadge, SourceBadge } from "@/components/badges";

/** Content of one block plus its two independent signals: review status and source evidence. */
export function BlockCard({ block, compact }: { block: Block; compact?: boolean }) {
  const p = block.payload as Record<string, unknown>;
  return (
    <span className={`block-card kind-${block.kind}`}>
      <span className="block-meta">
        <span className="kind">{KIND[block.kind]}</span>
        {block.kind === "worksheet_item" ? (
          <span className="muted small">
            {ITEM_TYPE[p.itemType as keyof typeof ITEM_TYPE]} · {SKILL[p.skill as keyof typeof SKILL]}
          </span>
        ) : null}
        <span className="spacer" />
        <ReviewBadge status={block.reviewStatus} />
        <SourceBadge block={block} />
        <IssueCounts block={block} />
      </span>
      <span className={compact ? "block-text clamp" : "block-text"}>{summarize(block)}</span>
      {/* Only the case that needs action: a stated reason is in the badge tooltip, the inspector and the review screen,
          so repeating it under every AI block only buries the blocks that do need attention. */}
      {block.transformation === "AI_PROPOSED" && !block.linkCount && !block.noSourceReason ? (
        <span className="no-source">AI đề xuất, chưa có nguồn và chưa ghi lý do.</span>
      ) : null}
    </span>
  );
}
