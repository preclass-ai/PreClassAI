import { describe, expect, it } from "vitest";
import { buildTree, childKinds, isLocked, summarize, type Block } from "@/lib/blocks";

function block(id: string, parentId: string | null, position: number, extra: Partial<Block> = {}): Block {
  return {
    id,
    parentId,
    position,
    kind: "paragraph",
    payload: { text: id },
    reviewStatus: "UNREVIEWED",
    transformation: "TEACHER_AUTHORED",
    contentHash: `h-${id}`,
    isFactual: false,
    remediationDraft: false,
    noSourceReason: null,
    revisionId: "r1",
    version: 1,
    linkCount: 0,
    blockerCount: 0,
    warningCount: 0,
    ...extra,
  };
}

describe("buildTree", () => {
  it("nests children under their parent and orders every level by position", () => {
    const tree = buildTree([block("c2", "p", 2), block("p", null, 1), block("root0", null, 0), block("c1", "p", 1)]);
    expect(tree.map((n) => n.block.id)).toEqual(["root0", "p"]);
    expect(tree[1]!.children.map((n) => n.block.id)).toEqual(["c1", "c2"]);
  });

  it("keeps a block whose parent is missing at the top level instead of dropping it", () => {
    expect(buildTree([block("orphan", "gone", 0)]).map((n) => n.block.id)).toEqual(["orphan"]);
  });
});

describe("summarize", () => {
  it("formats a data fact with value, unit and context", () => {
    const s = summarize({
      kind: "data_fact",
      payload: { label: "Dân số", value: 23.2, unit: "triệu người", region: "ĐB sông Hồng", period: "2023" },
    });
    expect(s).toContain("Dân số");
    expect(s).toContain("23,2 triệu người");
    expect(s).toContain("(ĐB sông Hồng, 2023)");
  });

  it("shows the correct option of an MCQ answer key and the value of a numeric one", () => {
    expect(summarize({ kind: "answer_key", payload: { correct: "B" } })).toBe("Đáp án đúng: B");
    expect(summarize({ kind: "answer_key", payload: { value: 5.4, unit: "triệu", tolerance: 0.05 } })).toBe(
      "Đáp số: 5,4 triệu (±0,05)",
    );
  });
});

describe("revision rules", () => {
  it("locks only published and superseded revisions", () => {
    expect(isLocked("DRAFT")).toBe(false);
    expect(isLocked("IN_REVIEW")).toBe(false);
    expect(isLocked("PUBLISHED")).toBe(true);
    expect(isLocked("SUPERSEDED")).toBe(true);
  });

  it("offers options, answer key and explanation only under a worksheet item", () => {
    expect(childKinds("worksheet_item")).toEqual(["option", "answer_key", "explanation"]);
    expect(childKinds("paragraph")).toEqual([]);
    expect(childKinds(null)).not.toContain("option");
  });
});
