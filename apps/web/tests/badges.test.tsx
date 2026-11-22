import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ReviewBadge, SourceBadge } from "@/components/badges";
import { valName } from "@/lib/labels";

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

describe("review badges", () => {
  it('"Máy đã kiểm" and "Đã duyệt" differ in colour and icon class', () => {
    render(<><ReviewBadge status="AUTO_CHECKED" /><ReviewBadge status="APPROVED" /></>);
    expect(screen.getByText("Máy đã kiểm")).toHaveClass("badge-machine");
    expect(screen.getByText("Máy đã kiểm")).not.toHaveClass("badge-success");
    expect(screen.getByText("Đã duyệt")).toHaveClass("badge-success");
  });

  it("validation rules get a plain name next to the code", () => {
    expect(valName("VAL-10")).toBe("Đề không lộ đáp án (VAL-10)");
    expect(valName("VAL-99")).toBe("VAL-99");
  });
});
