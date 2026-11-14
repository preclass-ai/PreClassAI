import { describe, expect, it } from "vitest";
import { safeNext } from "@/lib/redirect";

describe("safeNext", () => {
  it("keeps same-site paths with query", () => {
    expect(safeNext("/lessons/abc?tab=review")).toBe("/lessons/abc?tab=review");
  });

  it.each(["https://evil.com", "//evil.com", "/\\evil.com", "/\\/evil.com", "javascript:alert(1)", "/login", "", null])(
    "rejects %s",
    (next) => {
      expect(safeNext(next)).toBeNull();
    },
  );
});
