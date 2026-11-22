import { expect, test } from "vitest";
import { hintTier } from "@/lib/labels";

test("hints 1-3 are light, 4-7 clearer, 8-10 detailed", () => {
  expect([1, 3, 4, 7, 8, 10].map(hintTier)).toEqual([
    "Gợi ý nhẹ", "Gợi ý nhẹ", "Gợi ý rõ hơn", "Gợi ý rõ hơn", "Hướng dẫn chi tiết", "Hướng dẫn chi tiết",
  ]);
});
