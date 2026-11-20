import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { fmtDate, fmtDateTime } from "@/lib/format";
import StudentHome from "../app/(student)/student/page";

let guest = false;
vi.mock("@/lib/auth", () => ({ useAuth: () => ({ user: { isGuest: guest }, loading: false }) }));

afterEach(cleanup);

const item = (id: string, classCode: string) => ({
  id, title: `Bài ${id}`, classCode, openAt: "2026-11-01T00:00:00+07:00", dueAt: "2027-11-20T12:00:00+07:00",
  status: "NOT_STARTED", answeredCount: 0, itemCount: 2,
});

function renderHome() {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  client.setQueryData(["student-assignments"], { items: [item("a", "10A1"), item("b", "KS")] });
  return render(
    <QueryClientProvider client={client}>
      <StudentHome />
    </QueryClientProvider>,
  );
}

it("dates read dd/mm/yyyy with a four-digit year", () => {
  expect(fmtDate("2027-11-20T12:00:00+07:00")).toBe("20/11/2027");
  expect(fmtDateTime("2027-11-20T12:00:00+07:00")).toContain("20/11/2027");
});

it("a normal student sees the due date of a class assignment, but never one for the survey class KS", () => {
  guest = false;
  renderHome();
  expect(screen.getAllByText(/Hạn nộp/)).toHaveLength(1); // 10A1 only: KS has none
  expect(screen.getByText(/Hạn nộp 20\/11\/2027/)).toBeTruthy();
});

it("an anonymous guest sees no due date at all", () => {
  guest = true;
  renderHome();
  expect(screen.queryByText(/Hạn nộp/)).toBeNull();
});
