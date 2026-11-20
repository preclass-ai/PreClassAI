import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const put = vi.fn();
const del = vi.fn();
vi.mock("@/lib/api", () => ({
  unwrap: (p: unknown) => p,
  api: {
    GET: async (path: string) => (path === "/v1/auth/config" ? { guestEnabled: false, chatEnabled: true, personalizationEnabled: true } : { preferences: {} }),
    PUT: (...a: unknown[]) => put(...a),
    DELETE: (...a: unknown[]) => del(...a),
  },
}));

import { FocusTimer, PersonalizationBar } from "@/features/personalization";

const wrap = (ui: React.ReactNode) => render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);

beforeEach(() => {
  put.mockReset();
  del.mockReset();
});
afterEach(cleanup);

describe("PersonalizationBar", () => {
  it("offers neutral options, all off by default, with no labels about the student", async () => {
    wrap(<PersonalizationBar focus={false} onFocus={() => {}} />);
    expect(await screen.findByText("Em muốn học theo cách nào hôm nay?")).toBeInTheDocument();
    for (const l of ["Chia nhỏ từng bước", "Ưu tiên bảng số liệu", "Ưu tiên phần giải thích", "Nhắc tiến độ"]) {
      expect(screen.getByLabelText(l)).not.toBeChecked();
    }
    expect(document.body.textContent).not.toMatch(/mbti|adhd|tính cách|rối loạn|phong cách học/i);
  });

  it("saves one option at a time and can switch everything off", async () => {
    put.mockResolvedValue({ preferences: { chia_nho_tung_buoc: "on" } });
    del.mockResolvedValue({ preferences: {} });
    wrap(<PersonalizationBar focus={false} onFocus={() => {}} />);
    fireEvent.click(await screen.findByLabelText("Chia nhỏ từng bước"));
    await waitFor(() => expect(put).toHaveBeenCalledWith("/v1/student/preferences", { body: { preferences: { chia_nho_tung_buoc: "on" } } }));
    fireEvent.change(screen.getByLabelText("Hẹn giờ tập trung"), { target: { value: "10" } });
    await waitFor(() => expect(put).toHaveBeenCalledWith("/v1/student/preferences", { body: { preferences: { hen_gio_tap_trung: "10" } } }));
    fireEvent.click(screen.getByText("Tắt hết"));
    await waitFor(() => expect(del).toHaveBeenCalled());
  });

  it("focus mode toggles and records that it was used (survey flag) only once", async () => {
    put.mockResolvedValue({ preferences: { focus_mode_used: "on" } });
    const onFocus = vi.fn();
    wrap(<PersonalizationBar focus={false} onFocus={onFocus} />);
    fireEvent.click(await screen.findByText("Chế độ tập trung"));
    expect(onFocus).toHaveBeenCalledWith(true);
    await waitFor(() => expect(put).toHaveBeenCalledWith("/v1/student/preferences", { body: { preferences: { focus_mode_used: "on" } } }));
  });
});

describe("FocusTimer", () => {
  it("counts down and then gives a short, friendly break reminder", () => {
    vi.useFakeTimers();
    render(<FocusTimer minutes={5} />);
    expect(screen.getByRole("timer")).toHaveTextContent("05:00");
    act(() => void vi.advanceTimersByTime(61_000));
    expect(screen.getByRole("timer")).toHaveTextContent("03:59");
    act(() => void vi.advanceTimersByTime(5 * 60_000));
    expect(screen.getByText(/Em đã học 5 phút. Nghỉ mắt một chút/)).toBeInTheDocument();
    fireEvent.click(screen.getByText("Học tiếp"));
    expect(screen.getByRole("timer")).toHaveTextContent("05:00");
    vi.useRealTimers();
  });
});
