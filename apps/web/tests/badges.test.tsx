import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReviewBadge, SourceBadge } from "@/components/badges";

describe("status vs. evidence", () => {
  it("shows source evidence separately from review status (having a source ≠ correct)", () => {
    render(
      <>
        <ReviewBadge status="FLAGGED" />
        <SourceBadge block={{ linkCount: 3, transformation: "PARAPHRASED", noSourceReason: null }} />
      </>,
    );
    expect(screen.getByText("Có vấn đề")).toBeInTheDocument();
    expect(screen.getByText(/3 đoạn nguồn · Diễn đạt lại/)).toBeInTheDocument();
  });

  it("warns when an AI block has no source", () => {
    render(<SourceBadge block={{ linkCount: 0, transformation: "AI_PROPOSED", noSourceReason: null }} />);
    expect(screen.getByText(/Không có nguồn · AI đề xuất/)).toHaveClass("badge-warning");
  });
});
