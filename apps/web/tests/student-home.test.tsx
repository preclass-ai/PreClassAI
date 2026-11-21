import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import StudentHome from "../app/(student)/student/page";

vi.mock("@/lib/auth", () => ({ useAuth: () => ({ user: { isGuest: false }, loading: false }) }));

afterEach(cleanup);

it("summarizes assigned and unfinished Geography lessons from the returned list", () => {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  client.setQueryData(["student-assignments"], {
    items: [
      { id: "a", title: "Dân cư Việt Nam", classCode: "10A1", className: "10A1", openAt: "2026-11-01T00:00:00+07:00", dueAt: "2026-11-30T23:59:00+07:00", status: "IN_PROGRESS", answeredCount: 1, itemCount: 3 },
      { id: "b", title: "Rừng nhiệt đới", classCode: "10A1", className: "10A1", openAt: "2026-11-01T00:00:00+07:00", dueAt: "2026-11-30T23:59:00+07:00", status: "DONE", answeredCount: 3, itemCount: 3 },
    ],
    nextCursor: null,
  });
  render(<QueryClientProvider client={client}><StudentHome /></QueryClientProvider>);

  expect(screen.getByText("1 bài cần làm")).toBeInTheDocument();
  expect(screen.getByText(/1 bài đã xong/)).toBeInTheDocument();
  expect(screen.queryByText(/DỮ LIỆU MINH HỌA/)).toBeNull(); // no label on every page
  expect(screen.getAllByText("Địa lí · 10A1")).toHaveLength(2); // subject and class name stay on the card
});
