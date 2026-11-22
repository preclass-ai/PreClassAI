import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";
import { GettingStarted } from "@/features/getting-started";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  localStorage.clear();
});

it("shows three steps, closes, and stays closed next time", () => {
  render(<GettingStarted role="student" />);
  expect(screen.getAllByRole("listitem")).toHaveLength(3);
  fireEvent.click(screen.getByRole("button", { name: "Đóng khung 3 bước bắt đầu" }));
  expect(screen.queryByText("3 bước bắt đầu")).toBeNull();
  cleanup();
  render(<GettingStarted role="student" />);
  expect(screen.queryByText("3 bước bắt đầu")).toBeNull();
  cleanup();
  render(<GettingStarted role="teacher" />); // closed per role
  expect(screen.getByText("3 bước bắt đầu")).toBeTruthy();
});

it("works when localStorage throws", () => {
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  render(<GettingStarted role="teacher" />);
  expect(screen.getByText("3 bước bắt đầu")).toBeTruthy();
  fireEvent.click(screen.getByRole("button", { name: "Đóng khung 3 bước bắt đầu" }));
  expect(screen.queryByText("3 bước bắt đầu")).toBeNull();
});
