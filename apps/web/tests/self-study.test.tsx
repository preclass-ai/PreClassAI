import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/auth", () => ({ useAuth: () => ({ user: { id: "u1", isGuest: false }, loading: false }) }));
vi.mock("next/navigation", () => ({ usePathname: () => "/student/tu-hoc", useRouter: () => ({ push: vi.fn() }) }));

import SelfStudyPage from "../app/(student)/student/tu-hoc/page";
import { answerFaq } from "@/features/garden/faq";
import { SPECIES_BY_ID } from "@/features/garden/species";
import { coachLine } from "@/features/self-study/coach";
import { METHOD_BY_ID, METHODS, PROBLEMS } from "@/features/self-study/methods";

beforeAll(() => {
  window.matchMedia = ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia;
});
afterEach(() => {
  cleanup();
  localStorage.clear();
});

describe("Tự học", () => {
  it("every problem points to methods that exist", () => {
    for (const p of PROBLEMS) for (const id of p.methods) expect(METHOD_BY_ID.has(id)).toBe(true);
    for (const m of METHODS) expect(m.steps.length).toBeGreaterThanOrEqual(3);
  });

  it("the planted mascot recommends a method and walks the student through it", () => {
    localStorage.setItem("preclass.garden.u1", JSON.stringify({ species: "sakura", plantedAt: "2026-11-01", tours: ["home"] }));
    const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
    client.setQueryData(["student-assignments"], { items: [], nextCursor: null });
    render(<QueryClientProvider client={client}><SelfStudyPage /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Gặp bảng số liệu, biểu đồ là rối" }));
    fireEvent.click(screen.getByRole("button", { name: /Học Đọc bảng số liệu, biểu đồ cùng Bé Đào/ }));

    const coach = screen.getByRole("dialog", { name: "Bé Đào hướng dẫn Đọc bảng số liệu, biểu đồ" });
    expect(within(coach).getByText(/Bé Đào cùng em thử/)).toBeInTheDocument();
    fireEvent.click(within(coach).getByRole("button", { name: "Xong bước này ✓" }));
    expect(within(coach).getByText("Bước 2/5", { exact: false })).toBeInTheDocument();
    for (let i = 0; i < 4; i++) fireEvent.click(within(coach).getAllByRole("button", { name: /Xong bước này|Hoàn thành/ })[0]!);
    expect(within(coach).getByText(/Em đã đi hết 5 bước/)).toBeInTheDocument();
    expect(JSON.parse(localStorage.getItem("preclass.selfstudy") ?? "{}").chart).toHaveLength(5);
    fireEvent.click(within(coach).getByRole("button", { name: "Xong rồi!" }));
    expect(screen.getByText("1/8")).toBeInTheDocument(); // methods tried in full
  });

  it("the mascot chat sends study questions to the Tự học tab", () => {
    const ctx = { species: SPECIES_BY_ID.lotus, progress: null, onAssignment: false };
    const a = answerFaq("Có phương pháp học trước nào không?", ctx);
    expect(a.actions?.[0]?.action).toBe("selfstudy");
    expect(a.text).toContain(ctx.species.mascot);
    expect(coachLine(METHOD_BY_ID.get("sq3r")!, 0, "Bé Sen")).toMatch(/^Bé Sen cùng em thử SQ3R/);
  });
});
