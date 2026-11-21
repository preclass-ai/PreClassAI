import { describe, expect, it } from "vitest";
import { dueDayBefore } from "@/lib/format";

describe("dueDayBefore", () => {
  it("is 23:59 of the day before the lesson", () => {
    expect(dueDayBefore("2026-11-25")).toBe("2026-11-24T23:59");
  });
  it("crosses month and year borders", () => {
    expect(dueDayBefore("2026-12-01")).toBe("2026-11-30T23:59");
    expect(dueDayBefore("2027-01-01")).toBe("2026-12-31T23:59");
  });
});
