import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";
import { ClassProgressBoard, needsAttention, onBoard, phaseOf, reminderText, sortRows, summarize, toRow } from "@/features/class-progress";

afterEach(cleanup);

const NOW = Date.parse("2026-11-24T10:00:00+07:00");
const H = 3_600_000;
const iso = (ms: number) => new Date(ms).toISOString();
const cls = { id: "c1", code: "10A1" };
const A = (id: string, openOffsetH: number, dueOffsetH: number) => ({
  id,
  classCode: "10A1",
  classId: "c1",
  dueAt: iso(NOW + dueOffsetH * H),
  openAt: iso(NOW + openOffsetH * H),
  lessonId: "l1",
  lessonTitle: id,
  publishedVersionId: "p1",
  revisionNo: 1,
  studentTitle: `Bài ${id}`,
});
const P = (id: string, studentCount: number, completedCount: number, inProgressCount: number) => ({ assignmentId: id, studentCount, completedCount, inProgressCount, items: [] });

describe("progress rules", () => {
  it("puts each assignment in a phase and keeps recent ones on the board", () => {
    expect(phaseOf(A("x", 1, 30), NOW)).toBe("upcoming");
    expect(phaseOf(A("x", -10, 30), NOW)).toBe("soon");
    expect(phaseOf(A("x", -10, 72), NOW)).toBe("open");
    expect(phaseOf(A("x", -100, -2), NOW)).toBe("closed");
    expect(onBoard(A("x", -500, -24 * 13), NOW)).toBe(true);
    expect(onBoard(A("x", -500, -24 * 15), NOW)).toBe(false);
    expect(onBoard(A("x", 2, 30), NOW)).toBe(false);
  });

  it("counts students who have not started and flags assignments that need a reminder", () => {
    const soon = toRow(cls, A("soon", -10, 20), P("soon", 30, 10, 8), NOW);
    expect(soon.todo).toBe(12);
    expect(needsAttention(soon, NOW)).toBe(true);
    const open = toRow(cls, A("open", -10, 200), P("open", 30, 2, 0), NOW);
    expect(needsAttention(open, NOW)).toBe(false); // far from due: no alarm yet
    const finished = toRow(cls, A("done", -10, 20), P("done", 30, 30, 0), NOW);
    expect(needsAttention(finished, NOW)).toBe(false);
    const late = toRow(cls, A("late", -100, -30), P("late", 30, 25, 0), NOW);
    expect(needsAttention(late, NOW)).toBe(true);
    expect(sortRows([late, open, soon]).map((r) => r.a.id)).toEqual(["soon", "open", "late"]);

    const s = summarize([soon, open, late], NOW);
    expect(s.scope).toBe("open"); // the closed one stays out of the totals
    expect(s.todo).toBe(12 + 28);
    expect(s.rate).toBeCloseTo(12 / 60);
    expect(s.urgent).toBe(2);
  });

  it("treats an older API without counts as not loaded", () => {
    const r = toRow(cls, A("x", -10, 20), { assignmentId: "x", studentCount: 30, items: [] } as never, NOW);
    expect(r.loaded).toBe(false);
    expect(needsAttention(r, NOW)).toBe(false);
  });

  it("writes a reminder the teacher can paste into the class chat, addressing students as em", () => {
    const text = reminderText(toRow(cls, A("soon", -10, 20), P("soon", 30, 10, 8), NOW));
    expect(text).toContain("Lớp 10A1");
    expect(text).toContain("Còn 20 em chưa làm xong (8 em đang làm dở)");
  });
});

describe("board", () => {
  it("shows the totals, a bar per assignment, and the reminder list", () => {
    const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
    const now = Date.now();
    const a1 = { ...A("a1", 0, 0), openAt: iso(now - 10 * H), dueAt: iso(now + 20 * H) };
    const a2 = { ...A("a2", 0, 0), openAt: iso(now - 10 * H), dueAt: iso(now + 200 * H) };
    client.setQueryData(["classes"], { items: [{ id: "c1", code: "10A1", grade: 10, isSurvey: false, studentCount: 30 }] });
    client.setQueryData(["class-assignments", "c1"], { items: [a1, a2] });
    client.setQueryData(["progress", "c1", "a1"], P("a1", 30, 10, 8));
    client.setQueryData(["progress", "c1", "a2"], P("a2", 30, 30, 0));
    render(<QueryClientProvider client={client}><ClassProgressBoard /></QueryClientProvider>);

    expect(screen.getByRole("img", { name: /Bài a1, lớp 10A1: 10 em đã xong, 8 em đang làm, 12 em chưa làm, trên 30 em/ })).toBeInTheDocument();
    const alerts = screen.getByRole("region", { name: "Cần nhắc học sinh" });
    expect(within(alerts).getByText("10A1 · Bài a1")).toBeInTheDocument();
    expect(within(alerts).queryByText(/Bài a2/)).toBeNull();
    expect(screen.getByText("67%")).toBeInTheDocument(); // 40 of 60 student-assignments finished

    fireEvent.click(screen.getByRole("checkbox", { name: /Chỉ bài cần nhắc/ }));
    expect(screen.queryByRole("img", { name: /Bài a2/ })).toBeNull();
  });
});
