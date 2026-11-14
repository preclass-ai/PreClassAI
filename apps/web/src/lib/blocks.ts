import type { Schemas } from "./api";
import { fmtNumber } from "./format";

export type Block = Schemas["BlockOut"];
export type BlockPayload = Block["payload"];

export interface BlockNode {
  block: Block;
  children: BlockNode[];
}

/** The API returns blocks flat (`parentId` + `position`); rebuild the tree, ordered by position. */
export function buildTree(blocks: readonly Block[]): BlockNode[] {
  const nodes = new Map<string, BlockNode>();
  for (const b of blocks) nodes.set(b.id, { block: b, children: [] });
  const roots: BlockNode[] = [];
  for (const node of nodes.values()) {
    const parent = node.block.parentId ? nodes.get(node.block.parentId) : undefined;
    (parent ? parent.children : roots).push(node);
  }
  const sort = (list: BlockNode[]) => {
    list.sort((a, b) => a.block.position - b.block.position);
    list.forEach((n) => sort(n.children));
  };
  sort(roots);
  return roots;
}

function str(p: BlockPayload, key: string): string | undefined {
  const v = (p as Record<string, unknown>)[key];
  return typeof v === "string" ? v : undefined;
}

function num(p: BlockPayload, key: string): number | undefined {
  const v = (p as Record<string, unknown>)[key];
  return typeof v === "number" ? v : undefined;
}

/** One-line human summary of a block's payload (used in lists, review queue and gate). */
export function summarize(block: Pick<Block, "kind" | "payload">): string {
  const p = block.payload;
  switch (block.kind) {
    case "data_fact": {
      const parts = [str(p, "label"), `${fmtNumber(num(p, "value"))} ${str(p, "unit") ?? ""}`.trim()];
      const ctx = [str(p, "region"), str(p, "period")].filter(Boolean).join(", ");
      return `${parts.filter(Boolean).join(": ")}${ctx ? ` (${ctx})` : ""}`;
    }
    case "worksheet_item":
      return str(p, "stem") ?? "";
    case "option":
      return `${str(p, "label") ?? "?"}. ${str(p, "text") ?? ""}`;
    case "answer_key": {
      const correct = str(p, "correct");
      if (correct) return `Đáp án đúng: ${correct}`;
      const value = num(p, "value");
      if (value !== undefined) {
        const tol = num(p, "tolerance");
        return `Đáp số: ${fmtNumber(value)} ${str(p, "unit") ?? ""}${tol ? ` (±${fmtNumber(tol)})` : ""}`.trim();
      }
      const rubric = (p as Record<string, unknown>).rubricPoints;
      return Array.isArray(rubric) ? `Ý chấm: ${rubric.join("; ")}` : "Đáp án";
    }
    default:
      return str(p, "text") ?? "";
  }
}

/** True when the revision can no longer be edited (PUBLISHED / SUPERSEDED are locked by the server). */
export function isLocked(state: Schemas["RevisionOut"]["state"]): boolean {
  return state === "PUBLISHED" || state === "SUPERSEDED";
}

/** Empty payload for a new block of each kind (all required fields present). */
export function emptyPayload(kind: Block["kind"]): BlockPayload {
  switch (kind) {
    case "data_fact":
      return { label: "", region: "", period: "", value: 0, unit: "" };
    case "worksheet_item":
      return { itemType: "MCQ", skill: "READ_TABLE", stem: "" };
    case "option":
      return { label: "A", text: "" };
    case "answer_key":
      return { correct: "A" };
    default:
      return { text: "" };
  }
}

/** Which child kinds make sense under a parent (top level when parent is null). */
export function childKinds(parent: Block["kind"] | null): Block["kind"][] {
  if (parent === null) return ["heading", "paragraph", "data_fact", "instruction", "worksheet_item", "card_front"];
  if (parent === "worksheet_item") return ["option", "answer_key", "explanation"];
  if (parent === "card_front") return ["card_back"];
  return [];
}
