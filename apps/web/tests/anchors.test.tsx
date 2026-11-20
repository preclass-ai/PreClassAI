import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { AnchorPreview, colName, locatorText } from "@/features/anchors";
import type { Schemas } from "@/lib/api";

afterEach(cleanup);

describe("locatorText per format", () => {
  it("PDF, XLSX, PPTX and DOCX locators read naturally", () => {
    expect(locatorText({ page: 3, para: 2 })).toBe("Trang 3, đoạn 2");
    expect(locatorText({ sheet: "Dân số", row: 4, col: 2 })).toBe("Sheet Dân số, ô C5");
    expect(locatorText({ slide: 4, shape: 1, para: 0 })).toBe("Slide 4, đoạn 1");
    expect(locatorText({ slide: 2, shape: 3, row: 1, col: 1 })).toBe("Slide 2, bảng hàng 2, cột 2");
    expect(locatorText({ table: 0, row: 2, col: 1 })).toBe("bảng 1, hàng 3, cột 2");
    expect(locatorText({ para_index: 0 })).toBe("đoạn 1");
  });

  it("converts column indexes to spreadsheet letters", () => {
    expect([0, 25, 26, 27, 701, 702].map(colName)).toEqual(["A", "Z", "AA", "AB", "ZZ", "AAA"]);
  });
});

const a = (id: string, locator: Record<string, unknown>, excerpt: string): Schemas["AnchorOut"] =>
  ({ id, code: id, kind: "PARAGRAPH", locator, excerpt, excerptHash: "h", numbers: [] }) as Schemas["AnchorOut"];

describe("AnchorPreview", () => {
  it("groups anchors by page / sheet / slide and opens only the first group", () => {
    const { container } = render(
      <AnchorPreview anchors={[a("1", { page: 1, para: 1 }, "Một"), a("2", { page: 1, para: 2 }, "Hai"), a("3", { page: 2, para: 1 }, "Ba")]} />,
    );
    expect(screen.getByText("Trang 1")).toBeInTheDocument();
    expect(screen.getByText("Trang 2")).toBeInTheDocument();
    const open = [...container.querySelectorAll("details")].map((d) => d.open);
    expect(open).toEqual([true, false]);
    expect(screen.getByText("Ba")).toBeInTheDocument(); // plain text, in the closed group's DOM
  });

  it("renders file text as plain text, never as HTML", () => {
    const { container } = render(<AnchorPreview anchors={[a("1", { sheet: "S", row: 0, col: 0 }, '<img src=x onerror="alert(1)">')]} />);
    expect(container.querySelector("img")).toBeNull();
    expect(screen.getByText(/<img src=x/)).toBeInTheDocument();
  });
});
