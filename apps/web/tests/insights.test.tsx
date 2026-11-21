import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const get = vi.fn();
const post = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", () => ({ unwrap: (p: unknown) => p, api: { GET: (...a: unknown[]) => get(...a), POST: (...a: unknown[]) => post(...a) } }));

import { Insights } from "@/features/insights";

const base = {
  assignmentId: "a", lessonId: "l", publishedRevisionId: "r", canPractice: true, studentCount: 15, askingStudents: 2, totalQuestions: 5,
  focusSkills: ["COMPARE"], llmAvailable: false,
  themes: [{ key: "start", label: "Chưa biết bắt đầu từ đâu", count: 2, examples: ["Em nên bắt đầu từ đâu?"] }],
  items: [{ itemBlockId: "i", position: 1, stem: "Vùng nào có số dân cao nhất?", skill: "COMPARE", answeredCount: 2, firstAttemptCorrectRate: 0, hintsUsed: 2, asks: 5 }],
};
const wrap = () => render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}><Insights classId="c" assignmentId="a" /></QueryClientProvider>);

beforeEach(() => {
  get.mockReset();
  post.mockReset();
});
afterEach(cleanup);

describe("Insights", () => {
  it("shows grouped questions and results, anonymously", async () => {
    get.mockResolvedValue(base);
    wrap();
    expect(await screen.findByText("Chưa biết bắt đầu từ đâu")).toBeInTheDocument();
    expect(screen.getByText(/5 câu hỏi từ 2\/15 học sinh/)).toBeInTheDocument();
    expect(screen.getByText(/Không hiện tên hay mã của học sinh/)).toBeInTheDocument();
    expect(screen.getByText("Em nên bắt đầu từ đâu?", { exact: false })).toBeInTheDocument();
    expect(screen.getByText("0%")).toBeInTheDocument();
  });

  it("the analysis button labels who wrote the summary", async () => {
    get.mockResolvedValue({ ...base, llmAvailable: true });
    post.mockResolvedValue({ topics: ["Nhiều em chưa biết bắt đầu từ đâu"], generatedBy: "llm" });
    wrap();
    fireEvent.click(await screen.findByRole("button", { name: "AI phân tích" }));
    expect(await screen.findByText("Nhiều em chưa biết bắt đầu từ đâu")).toBeInTheDocument();
    expect(screen.getByText(/Do AI tóm tắt, thầy cô kiểm tra lại/)).toBeInTheDocument();
  });

  it("the practice button only exists for the lesson's author and when there is a weak skill", async () => {
    get.mockResolvedValue({ ...base, canPractice: false });
    wrap();
    await screen.findByText("Chưa biết bắt đầu từ đâu");
    expect(screen.queryByRole("button", { name: "AI gợi ý bài tập thêm" })).toBeNull();
  });

  it("drafts practice through new revision then generate (append, focus skills), never publishes", async () => {
    get.mockResolvedValue(base);
    post.mockResolvedValue({ jobId: "j" });
    wrap();
    fireEvent.click(await screen.findByRole("button", { name: "AI gợi ý bài tập thêm" }));
    await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
    expect(post.mock.calls[0]![0]).toBe("/v1/revisions/{revision_id}/new-revision");
    expect(post.mock.calls[1]![0]).toBe("/v1/lessons/{lesson_id}/generate");
    expect(post.mock.calls[1]![1].body).toEqual({ outputType: "WORKSHEET", nItems: 3, focusSkills: ["COMPARE"], mode: "append" });
  });
});
