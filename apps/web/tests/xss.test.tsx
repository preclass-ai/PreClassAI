import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";
import { BlockCard } from "@/features/block-view";
import { EvidenceList } from "@/features/inspector";
import type { Block } from "@/lib/blocks";

afterEach(cleanup);

const PAYLOAD = '<img src=x onerror="window.__xss=1"><script>window.__xss=1</script>';

function block(kind: Block["kind"], payload: Record<string, unknown>): Block {
  return {
    id: "b1", parentId: null, position: 1, kind, payload, reviewStatus: "UNREVIEWED", transformation: "TEACHER_AUTHORED",
    contentHash: "h", isFactual: false, noSourceReason: null, revisionId: "r1", version: 1, linkCount: 0, blockerCount: 0,
    warningCount: 0,
  } as unknown as Block;
}

it("block text from the payload is rendered as text, never as HTML", () => {
  const { container } = render(
    <>
      <BlockCard block={block("paragraph", { text: PAYLOAD })} />
      <BlockCard block={block("heading", { text: PAYLOAD })} />
      <BlockCard block={block("data_fact", { label: PAYLOAD, value: 1, unit: PAYLOAD, region: PAYLOAD, period: "2020" })} />
    </>,
  );
  expect(container.querySelector("img, script, iframe, svg")).toBeNull();
  expect((window as unknown as { __xss?: number }).__xss).toBeUndefined();
  expect(container.textContent).toContain("<img src=x");
});

it("source excerpts from an anchor are rendered as text, never as HTML", () => {
  const link = {
    id: "l1", relation: "quoted_from", status: "VERIFIED",
    anchor: { id: "a1", code: "anc_x_001", kind: "PARAGRAPH", locator: {}, excerpt: PAYLOAD, excerptHash: "h", numbers: [] },
  };
  const { container } = render(<EvidenceList links={[link] as never} />);
  expect(container.querySelector("img, script, iframe")).toBeNull();
  expect(container.textContent).toContain("<img src=x");
  expect(screen.queryByRole("img")).toBeNull();
});
