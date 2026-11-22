import { describe, expect, it } from "vitest";
import { parseAnswerNumber } from "@/lib/format";

const value = (s: string) => {
  const r = parseAnswerNumber(s);
  return "value" in r ? r.value : null;
};

describe("parseAnswerNumber", () => {
  it("reads decimal comma and decimal point", () => {
    expect(value("17,3")).toBe(17.3);
    expect(value("17.3")).toBe(17.3);
    expect(value(" 17,3 ")).toBe(17.3);
    expect(value("-2,5")).toBe(-2.5);
    expect(value("0")).toBe(0);
  });
  it("reads Vietnamese digit grouping and spaces", () => {
    expect(value("1.234,5")).toBe(1234.5);
    expect(value("1.234.567")).toBe(1234567);
    expect(value("1 234")).toBe(1234);
    expect(value("1 234,5")).toBe(1234.5);
  });
  it("keeps a lone 1.234 as a decimal, as before", () => {
    expect(value("1.234")).toBe(1.234);
  });
  it("refuses what Number() would silently convert", () => {
    for (const s of ["0x11", "1e3", "Infinity", "-", ",5", "1,2,3", "1.2.3,4,5"]) expect(value(s)).toBeNull();
  });
  it("explains a unit or words instead of a number", () => {
    expect(parseAnswerNumber("17,3 triệu")).toEqual({ error: "Chỉ nhập số, không ghi đơn vị (ví dụ: 17,3)." });
    expect(parseAnswerNumber("abc")).toEqual({ error: "Chỉ nhập số, không ghi đơn vị (ví dụ: 17,3)." });
    expect(parseAnswerNumber("1,2,3")).toEqual({ error: "Đáp số chưa đúng dạng số (ví dụ: 17,3 hoặc -2,5)." });
  });
});
