import { expect, it } from "vitest";
import { dueDayBefore, dueNotBeforeLesson } from "@/lib/format";

it("warns when the lesson day is on or before the due day, not when the due time is the day before", () => {
  expect(dueNotBeforeLesson("2026-12-10", "2026-12-10T23:59")).toBe(true); // same day
  expect(dueNotBeforeLesson("2026-12-10", "2026-12-12T08:00")).toBe(true); // due after the lesson
  expect(dueNotBeforeLesson("2026-12-10", dueDayBefore("2026-12-10"))).toBe(false); // the default
  expect(dueNotBeforeLesson("", "2026-12-10T23:59")).toBe(false); // no lesson day
});
