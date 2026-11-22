import { describe, expect, it } from "vitest";
import { splitObjectives } from "@/lib/objectives";

const L = (...t: string[]) => t.map((text) => ({ text }));

describe("splitObjectives", () => {
  it("turns lettered group lines into headings, not bullets", () => {
    const g = splitObjectives(L("1. Kiến thức", "Nêu được đặc điểm dân cư.", "2. Năng lực", "a) Năng lực chung:", "Tự chủ và tự học.", "b) Năng lực đặc thù:", "Nhận thức khoa học địa lí.", "3. Phẩm chất", "Chăm chỉ."));
    expect(g.map((x) => x.title)).toEqual(["Kiến thức", "Năng lực", "Năng lực chung", "Năng lực đặc thù", "Phẩm chất"]);
    expect(g[0]?.items.map((i) => i.text)).toEqual(["Nêu được đặc điểm dân cư."]);
    expect(g[2]?.items.map((i) => i.text)).toEqual(["Tự chủ và tự học."]);
  });

  it("keeps the text after the colon as the first bullet of the group", () => {
    const g = splitObjectives(L("a) Năng lực chung: tự chủ và tự học.", "Giao tiếp và hợp tác."));
    expect(g).toHaveLength(1);
    expect(g[0]?.title).toBe("Năng lực chung");
    expect(g[0]?.items.map((i) => i.text)).toEqual(["tự chủ và tự học.", "Giao tiếp và hợp tác."]);
  });

  it("leaves ordinary objectives alone, even ones that mention a competency", () => {
    const g = splitObjectives(L("Nêu được khái niệm dân số.", "Vận dụng kiến thức đã học để giải thích hiện tượng."));
    expect(g).toEqual([{ title: null, items: L("Nêu được khái niệm dân số.", "Vận dụng kiến thức đã học để giải thích hiện tượng.") }]);
    expect(splitObjectives(L("Kiến thức về dân cư giúp em hiểu rõ hơn đặc điểm vùng miền nước ta."))[0]?.title).toBeNull();
  });
});
