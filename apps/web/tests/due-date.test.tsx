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

it("every student sees the due date of each assignment, including the survey class", () => {
  guest = false;
  renderHome();
  expect(screen.getAllByText(/Hạn nộp 20\/11\/2027/)).toHaveLength(2);
});

it("a guest sees it too, as dd/mm/yyyy", () => {
  guest = true;
  renderHome();
  expect(screen.getAllByText(/Hạn nộp 20\/11\/2027/).length).toBeGreaterThan(0);
});
