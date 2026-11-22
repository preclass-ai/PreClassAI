import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const get = vi.fn();
const patch = vi.fn();
const del = vi.fn();
vi.mock("@/lib/api", () => ({
  unwrap: (p: unknown) => p,
  api: { GET: (...a: unknown[]) => get(...a), PATCH: (...a: unknown[]) => patch(...a), DELETE: (...a: unknown[]) => del(...a) },
}));

import { AssignmentActions, LessonAssignments } from "@/features/assignments";

const A = {
  id: "a1", classId: "c1", classCode: "10A1", lessonId: "l1", lessonTitle: "Dân số", revisionNo: 2, publishedVersionId: "p",
  openAt: "2026-11-01T00:00:00+07:00", dueAt: "2026-11-30T00:00:00+07:00",
};
const wrap = (ui: React.ReactNode) => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>{ui}</QueryClientProvider>);

beforeEach(() => {
  get.mockReset();
  patch.mockReset();
  del.mockReset();
});
afterEach(cleanup);

it("changes the due time with the new value as ISO", async () => {
  patch.mockResolvedValue(A);
  wrap(<AssignmentActions classId="c1" assignment={A} />);
  fireEvent.click(screen.getByRole("button", { name: "Sửa hạn" }));
  fireEvent.change(screen.getByLabelText("Hạn nộp mới"), { target: { value: "2026-12-05T23:59" } });
  fireEvent.click(screen.getByRole("button", { name: "Lưu hạn" }));
  await waitFor(() => expect(patch).toHaveBeenCalledTimes(1));
  expect(patch.mock.calls[0]![1].body.dueAt).toBe(new Date("2026-12-05T23:59").toISOString());
});

it("cancel needs a second click and says what stays", async () => {
  del.mockResolvedValue(undefined);
  wrap(<AssignmentActions classId="c1" assignment={A} />);
  fireEvent.click(screen.getByRole("button", { name: "Hủy giao" }));
  expect(screen.getByText(/câu đã trả lời vẫn được giữ/)).toBeTruthy();
  expect(del).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Xác nhận hủy giao" }));
  await waitFor(() => expect(del).toHaveBeenCalledTimes(1));
});

it("the lesson page lists the classes it is assigned to, and nothing when none", async () => {
  get.mockResolvedValue({ items: [A] });
  wrap(<LessonAssignments lessonId="l1" />);
  expect(await screen.findByText(/Đã giao cho:/)).toBeTruthy();
  expect(screen.getByRole("link", { name: "10A1" })).toBeTruthy();
  cleanup();
  get.mockResolvedValue({ items: [] });
  const { container } = wrap(<LessonAssignments lessonId="l2" />);
  await waitFor(() => expect(get).toHaveBeenCalledTimes(2));
  expect(container.textContent).toBe("");
});
