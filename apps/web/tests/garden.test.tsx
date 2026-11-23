import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth", () => ({ useAuth: () => ({ user: { id: "u1", isGuest: false }, loading: false }) }));
vi.mock("@/features/habit-api", async (orig) => ({ ...(await orig<typeof import("@/features/habit-api")>()), askHabit: vi.fn() }));

import { answerFaq, normalize } from "@/features/garden/faq";
import { GardenCard } from "@/features/garden/garden-card";
import { progressOf, SPECIES_BY_ID, stageFor, stageRange, tasksToNext } from "@/features/garden/species";
import { HabitBar } from "@/features/habit";
import HabitChat from "@/features/habit-chat";
import { ThemeToggle } from "@/lib/theme";

beforeAll(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.show = HTMLDialogElement.prototype.showModal;
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  window.matchMedia = ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia;
});
beforeEach(() => {
  localStorage.clear();
  delete document.documentElement.dataset.theme;
});
afterEach(cleanup);

const A = (id: string, status: "NOT_STARTED" | "IN_PROGRESS" | "DONE" | "CLOSED", dueAt: string, itemCount = 3) => ({ id, title: id, status, dueAt, itemCount });

describe("growth by finished assignments", () => {
  it("maps finished assignments to seven stages", () => {
    expect([0, 1, 2, 3, 4, 5, 7, 8, 11, 12, 15, 16, 40].map(stageFor)).toEqual([0, 1, 1, 2, 2, 3, 3, 4, 4, 5, 5, 6, 6]);
    expect(stageRange(0)).toBe("0 bài");
    expect(stageRange(1)).toBe("1–2 bài");
    expect(stageRange(6)).toBe("16+ bài");
    expect(tasksToNext(6)).toBe(2);
    expect(tasksToNext(20)).toBeNull();
  });
  it("counts the streak over assignments: open ones wait, a missed one resets, days without assignments do nothing", () => {
    const p = progressOf([
      A("t1", "DONE", "2026-09-01T00:00:00Z"),
      A("t2", "CLOSED", "2026-09-10T00:00:00Z"), // missed
      A("t3", "DONE", "2026-10-01T00:00:00Z"),
      A("t4", "DONE", "2026-12-20T00:00:00Z"), // finished early, after a long holiday gap
      A("t5", "IN_PROGRESS", "2026-12-01T00:00:00Z"), // still open: does not break
      A("t6", "CLOSED", "2026-08-01T00:00:00Z", 0), // empty assignment: ignored
    ]);
    expect(p.streak).toBe(2);
    expect(p.done).toBe(3); // the tree never shrinks: the missed one does not take anything away
    expect(p.pending.map((a) => a.id)).toEqual(["t5"]);
  });
});

describe("mascot how-to answers", () => {
  const ctx = { species: SPECIES_BY_ID.sakura, progress: { done: 4, streak: 2, pending: [] }, onAssignment: false };
  it("matches Vietnamese with or without diacritics", () => {
    expect(normalize("Gợi Ý dùng sao?")).toBe("goi y dung sao");
    expect(answerFaq("goi y dung sao", ctx).text).toMatch(/gợi ý cụ thể hơn một bậc/);
    expect(answerFaq("Làm sao bật chế độ tối?", ctx).actions?.[0]?.action).toBe("theme");
    expect(answerFaq("cây lớn thế nào", ctx).text).toMatch(/Mầm non/);
  });
  it("sends lesson questions to HABIT AI and never answers them itself", () => {
    expect(answerFaq("thủ đô của Pháp là gì", ctx).text).toMatch(/Hỏi HABIT AI/);
  });
});

function withClient(ui: React.ReactNode) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: Infinity } } });
  client.setQueryData(["auth-config"], { chatEnabled: true });
  const items = [...Array(9)].map((_, i) => A(`d${i}`, "DONE", `2026-10-${String(i + 1).padStart(2, "0")}T00:00:00Z`));
  items.push(A("open", "NOT_STARTED", "2026-11-30T16:59:00Z"));
  client.setQueryData(["student-assignments"], { items, nextCursor: null });
  return render(<QueryClientProvider client={client}>{ui}</QueryClientProvider>);
}

describe("garden card", () => {
  it("asks for a seed first", () => {
    withClient(<GardenCard />);
    expect(screen.getByRole("button", { name: "Chọn hạt giống" })).toBeInTheDocument();
  });
  it("grows the chosen tree with finished assignments", () => {
    localStorage.setItem("preclass.garden.u1", JSON.stringify({ species: "apple", tours: [] }));
    withClient(<GardenCard />);
    expect(screen.getByRole("heading", { name: "Ra hoa" })).toBeInTheDocument(); // 9 finished: stage 4
    expect(screen.getByText(/Còn 3 bài nữa là tới “Kết trái”/)).toBeInTheDocument();
    expect(screen.getByText(/bài liên tiếp/).textContent).toContain("9");
    expect(screen.getByText(/Bài “open” hạn/)).toBeInTheDocument();
    expect(screen.getByRole("list", { name: "Các giai đoạn phát triển" }).querySelector('[aria-current="step"]')).toHaveTextContent("8–11 bài");
  });
});

describe("HABIT AI chat with the mascot", () => {
  it("speaks as the student's mascot but keeps the HABIT AI rules", () => {
    render(<HabitChat assignmentId="a" itemId="i" answered={false} explanation={null} open onClose={() => {}} mascot={{ species: SPECIES_BY_ID.lotus, stage: 3 }} />);
    expect(screen.getByRole("dialog", { name: "Hỏi HABIT AI" })).toBeInTheDocument();
    expect(screen.getByText(/Bé Sen đây! Mình cùng em nghĩ câu này/)).toBeInTheDocument();
    expect(screen.getByText(/HABIT AI không đưa đáp án/)).toBeInTheDocument();
  });
});

describe("theme toggle", () => {
  it("switches dark mode and remembers it", () => {
    render(<ThemeToggle />);
    const sw = screen.getByRole("switch", { name: "Chế độ tối" });
    expect(sw).toHaveAttribute("aria-checked", "false");
    fireEvent.click(sw);
    expect(document.documentElement.dataset.theme).toBe("dark");
    expect(localStorage.getItem("preclass.theme")).toBe("dark");
    expect(sw).toHaveAttribute("aria-checked", "true");
  });
});

describe("habit bar on an assignment", () => {
  it("says how many questions are left before the streak goes up, with no daily goal", () => {
    withClient(<HabitBar assignmentId="open" answered={1} total={3} closed={false} />);
    const bar = screen.getByRole("region", { name: "Thói quen học của em" });
    expect(bar).toHaveTextContent("Chuỗi 9 bài");
    expect(bar).toHaveTextContent("Còn 2 câu nữa là xong bài, chuỗi lên 🔥 10.");
    expect(bar).not.toHaveTextContent(/Mục tiêu hôm nay/);
  });
  it("does not blame the student when the assignment is over", () => {
    withClient(<HabitBar assignmentId="open" answered={1} total={3} closed />);
    expect(screen.getByRole("region", { name: "Thói quen học của em" })).toHaveTextContent("cây của em vẫn giữ nguyên");
  });
});
