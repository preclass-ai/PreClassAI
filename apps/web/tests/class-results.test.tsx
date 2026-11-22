import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import ClassesPage from "../app/(teacher)/classes/page";

vi.mock("@/lib/auth", () => ({ RequireRole: ({ children }: { children: React.ReactNode }) => <>{children}</> }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), useSearchParams: () => new URLSearchParams("assignment=a1") }));
vi.mock("@/features/insights", () => ({ Insights: () => null }));

afterEach(cleanup);

const CLASS = "c1";
const ASSIGN = "a1";
const ITEMS = [{ itemBlockId: "q1", stem: "Câu một", answeredCount: 2, firstAttemptCorrectRate: 0.5 }];

function renderWith(progress: Record<string, unknown>) {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  client.setQueryData(["classes"], { items: [{ id: CLASS, code: "10A1", grade: 10, studentCount: 15 }] });
  client.setQueryData(["class-assignments", CLASS], {
    items: [{ id: ASSIGN, lessonTitle: "Bài A", openAt: "2026-11-01T00:00:00+07:00", dueAt: "2026-11-30T00:00:00+07:00" }],
  });
  client.setQueryData(["progress", CLASS, ASSIGN], { assignmentId: ASSIGN, studentCount: 15, items: ITEMS, ...progress });
  render(
    <QueryClientProvider client={client}>
      <ClassesPage />
    </QueryClientProvider>,
  );
}

it("shows how many students finished and a link to the class results CSV", () => {
  renderWith({ completedCount: 9, inProgressCount: 3 });
  expect(screen.getByText(/9\/15 em đã làm xong · 3 em đang làm · 3 em\s+chưa làm/)).toBeTruthy();
  const link = screen.getByRole("link", { name: "Tải kết quả (CSV)" });
  expect(link.getAttribute("href")).toBe(`/v1/classes/${CLASS}/assignments/${ASSIGN}/results.csv`);
});

it("an older API without the counts shows neither the summary nor the download (no undefined/NaN)", () => {
  renderWith({});
  expect(screen.queryByRole("link", { name: "Tải kết quả (CSV)" })).toBeNull();
  expect(document.body.textContent).not.toMatch(/undefined|NaN/);
  expect(screen.getByText(/Câu một/)).toBeTruthy();
});
