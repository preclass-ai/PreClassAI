import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

const patch = vi.fn();
vi.mock("@/lib/api", () => ({ unwrap: (p: unknown) => p, api: { PATCH: (...a: unknown[]) => patch(...a) } }));

import { LessonTitleForm } from "@/features/lesson-title";
import { checkTitle } from "@/lib/title";

const L = (over: object = {}) =>
  ({ id: "l1", title: "Bài cũ", goal: "Mục tiêu cũ", grade: 10, authorId: "u", createdAt: "x", publishedVersionId: null,
     currentRevision: { id: "r", state: "DRAFT" }, ...over }) as never;
const wrap = (ui: React.ReactNode) => render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);

beforeEach(() => patch.mockReset());
afterEach(cleanup);

it("checks 3 to 120 characters after trimming", () => {
  expect(checkTitle("   ")).toMatch(/không được để trống/);
  expect(checkTitle(" ab ")).toMatch(/ít nhất 3/);
  expect(checkTitle("a".repeat(121))).toMatch(/không quá 120/);
  expect(checkTitle("  Bài   4  ")).toBeNull();
});

it("saves the trimmed title and the goal, and stays disabled while unchanged or invalid", async () => {
  patch.mockResolvedValue({});
  wrap(<LessonTitleForm lesson={L()} />);
  const save = screen.getByRole("button", { name: "Lưu" }) as HTMLButtonElement;
  expect(save.disabled).toBe(true);
  fireEvent.change(screen.getByLabelText(/^Tên bài/), { target: { value: "x" } });
  expect(save.disabled).toBe(true);
  fireEvent.change(screen.getByLabelText(/^Tên bài/), { target: { value: "  Bài 4.   Trái Đất " } });
  fireEvent.change(screen.getByLabelText(/^Mục tiêu/), { target: { value: "Mô tả được" } });
  fireEvent.click(save);
  await waitFor(() => expect(patch).toHaveBeenCalledTimes(1));
  expect(patch.mock.calls[0]![1].body).toEqual({ title: "Bài 4. Trái Đất", goal: "Mô tả được" });
  expect(await screen.findByText("Đã lưu")).toBeTruthy();
});

it("tells the teacher a published lesson's new name applies to the next publish", () => {
  wrap(<LessonTitleForm lesson={L()} />);
  expect(screen.queryByText(/Tên mới áp dụng khi xuất bản bản tiếp theo/)).toBeNull();
  cleanup();
  wrap(<LessonTitleForm lesson={L({ publishedVersionId: "p", currentRevision: { id: "r", state: "PUBLISHED" } })} />);
  expect(screen.getByText(/Tên mới áp dụng khi xuất bản bản tiếp theo/)).toBeTruthy();
});
