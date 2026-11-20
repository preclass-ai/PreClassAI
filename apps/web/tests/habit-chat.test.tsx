import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeAll, beforeEach, describe, expect, it, vi } from "vitest";
import { ApiError } from "@/lib/api";

const ask = vi.fn();
// plain wrapper: vitest tracks promises returned by vi.fn(), which reports an intentional rejection as an unhandled error
let reject: ApiError | null = null;
vi.mock("@/features/habit-api", () => ({
  askHabit: (...a: unknown[]) => (reject ? Promise.reject(reject) : Promise.resolve(ask(...a))),
}));

import HabitChat from "@/features/habit-chat";

beforeAll(() => {
  // jsdom has no <dialog> methods
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute("open", ""); };
  HTMLDialogElement.prototype.show = HTMLDialogElement.prototype.showModal;
  HTMLDialogElement.prototype.close = function () { this.removeAttribute("open"); };
  window.matchMedia = ((q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {} })) as unknown as typeof window.matchMedia;
});
beforeEach(() => {
  ask.mockReset();
  reject = null;
});
afterEach(cleanup);

const mount = () => render(<HabitChat assignmentId="a" itemId="i" answered={false} explanation={null} open onClose={() => {}} />);

describe("Habit chat", () => {
  it("shows the no-answer and no-personal-data notes and a 300 character counter", () => {
    mount();
    expect(screen.getByText(/Habit không đưa đáp án/)).toBeInTheDocument();
    expect(screen.getByText(/Không nhập thông tin cá nhân/)).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Câu hỏi cho Habit"), { target: { value: "abc" } });
    expect(screen.getByText("3/300")).toBeInTheDocument();
    expect(screen.getByLabelText("Câu hỏi cho Habit")).toHaveAttribute("maxlength", "300");
  });

  it("renders a reply as plain text, never as HTML", async () => {
    ask.mockResolvedValue({ reply: '<img src=x onerror="alert(1)"> **đậm**', hintLevel: 0, sourceRefs: [], blockedReason: null });
    const { container } = mount();
    fireEvent.click(screen.getByText("Em nên bắt đầu từ đâu?"));
    await screen.findByText(/<img src=x/);
    expect(container.querySelector("img")).toBeNull();
    expect(ask).toHaveBeenCalledWith("a", expect.objectContaining({ action: "ask", message: "Em nên bắt đầu từ đâu?" }));
  });

  it("shows the source label and marks a refusal", async () => {
    ask.mockResolvedValue({ reply: "Habit không đưa đáp án — em tự làm nhé!", hintLevel: 0, blockedReason: "ANSWER_REQUEST",
      sourceRefs: [{ blockId: "b", label: "Đoạn văn", excerpt: "Dân cư phân bố không đều" }] });
    mount();
    fireEvent.change(screen.getByLabelText("Câu hỏi cho Habit"), { target: { value: "đáp án là gì" } });
    fireEvent.click(screen.getByText("Gửi"));
    expect(await screen.findByText(/Nguồn đã được thầy cô duyệt · Đoạn văn/)).toBeInTheDocument();
    expect(document.querySelector(".habit-msg.refused")).not.toBeNull();
  });

  it("friendly message and locked input on 429; retry reuses the same requestId after a network error", async () => {
    ask.mockRejectedValueOnce(new ApiError({ type: "x", title: "t", detail: "t", status: 0, code: "NETWORK" }));
    ask.mockResolvedValue({ reply: "ok", hintLevel: 0, sourceRefs: [], blockedReason: null });
    mount();
    fireEvent.change(screen.getByLabelText("Câu hỏi cho Habit"), { target: { value: "số liệu ở đâu" } });
    fireEvent.click(screen.getByText("Gửi"));
    fireEvent.click(await screen.findByText("Thử lại"));
    await waitFor(() => expect(ask).toHaveBeenCalledTimes(2));
    expect(ask.mock.calls[1]![1].requestId).toBe(ask.mock.calls[0]![1].requestId);
  });

  it("locks the input after CHAT_LIMIT", async () => {
    reject = new ApiError({ type: "x", title: "t", detail: "t", status: 429, code: "CHAT_LIMIT" });
    mount();
    fireEvent.click(screen.getByText("Công thức tính là gì?"));
    expect(await screen.findByText("Hôm nay em hỏi nhiều rồi, thử tự làm nhé!")).toBeInTheDocument();
    expect(screen.getByLabelText("Câu hỏi cho Habit")).toBeDisabled();
  });
});
