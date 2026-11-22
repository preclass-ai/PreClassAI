import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import type { ReactNode } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const put = vi.fn();
vi.mock("@/lib/api", async (orig) => {
  const real = await orig<typeof import("@/lib/api")>();
  return { ...real, api: { PUT: (...a: unknown[]) => put(...a) }, unwrap: (p: Promise<unknown>) => p };
});

import { ReviewAsk, ReviewStepper, Steps } from "@/features/review-step";

const cards = [
  { id: "c1", position: 1, title: "Dân số", points: ["Ý một", "Ý hai"], example: "Ví dụ một", check: { statement: "Câu một", answerTrue: true, explanation: "Vì giáo án nêu vậy." } },
  { id: "c2", position: 2, title: "Phân bố", points: ["Ý ba", "Ý bốn"], example: "Ví dụ hai", check: { statement: "Câu hai", answerTrue: false, explanation: "Sai vì ngược lại." } },
];
const state = { choice: "not_yet" as const, seenIds: [], checks: {}, reviewed: false };
const wrap = (ui: ReactNode) => render(<QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>);

beforeEach(() => {
  put.mockReset();
  put.mockResolvedValue({});
});
afterEach(cleanup);

describe("Quick review before the quiz", () => {
  it("asks once whether the student has learned the lesson and saves the choice", async () => {
    const onChoose = vi.fn();
    wrap(<ReviewAsk assignmentId="a" onChoose={onChoose} onSaved={() => {}} />);
    expect(screen.getByText("Em đã học bài này chưa?")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Rồi, làm luôn"));
    expect(onChoose).toHaveBeenCalledWith("done");
    await waitFor(() => expect(put).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ body: { choice: "done" } })));
  });

  it("shows two steps, the first current while reviewing", () => {
    wrap(<Steps stage="review" />);
    expect(screen.getByText("1. Ôn nhanh")).toHaveAttribute("aria-current", "step");
    expect(screen.getByText("2. Làm bài kiểm tra")).not.toHaveAttribute("aria-current");
  });

  it("saves seen cards and the self-check result with an immediate explanation, then opens the quiz on 'Đủ rồi'", async () => {
    const onDone = vi.fn();
    put.mockImplementation((_p: unknown, o: { body: { reviewed?: boolean } }) => Promise.resolve(o.body));
    wrap(<ReviewStepper assignmentId="a" cards={cards} state={state} onSaved={() => {}} onDone={onDone} />);
    expect(screen.getByText("Thẻ 1/2 · không tính điểm")).toBeInTheDocument();
    await waitFor(() => expect(put).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ body: { seenIds: ["c1"] } })));
    fireEvent.click(screen.getByText("Đúng"));
    expect(await screen.findByText("Vì giáo án nêu vậy.")).toBeInTheDocument();
    expect(put).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ body: { checks: { c1: true } } }));
    expect(onDone).not.toHaveBeenCalled(); // the quiz stays closed until the review is done or skipped
    fireEvent.click(screen.getByText("Đủ rồi, làm bài"));
    await waitFor(() => expect(onDone).toHaveBeenCalled());
    expect(put).toHaveBeenCalledWith(expect.anything(), expect.objectContaining({ body: { reviewed: true } }));
  });

  it("opens at the card HABIT AI pointed to", async () => {
    wrap(<ReviewStepper assignmentId="a" cards={cards} state={state} startId="c2" onSaved={() => {}} onDone={() => {}} />);
    expect(await screen.findByText("Phân bố")).toBeInTheDocument();
    expect(screen.getByText("Xong, làm bài")).toBeInTheDocument(); // last card
  });
});
