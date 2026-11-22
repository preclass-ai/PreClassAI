import path from "node:path";
import { expect, test, type APIRequestContext } from "@playwright/test";
import { login } from "./helpers";

// Teacher uploads a lesson plan, AI drafts questions and review cards, the teacher approves some, publishes and assigns;
// the student reviews first, then does the quiz, asks HABIT AI five questions and uses all 10 hints.
// Needs the API with CHAT_ENABLED=true QUIZ_GEN_ENABLED=true QUIZ_GEN_MOCK=true (the mock model builds drafts from the plan text).
const STUDENT: Record<string, string> = { "mobile-390": "HS10-01", "tablet-768": "HS10-02", "desktop-1280": "HS10-03", "webkit-390": "HS10-04" };
const H = { "X-PreClass-CSRF": "1" };
const shot = (name: string, project: string) => `test-results/ai-quiz/${name}-${project}.png`;

async function ok<T>(r: Awaited<ReturnType<APIRequestContext["get"]>>): Promise<T> {
  expect(r.ok(), `${r.url()} ${r.status()} ${await r.text()}`).toBeTruthy();
  return (await r.json()) as T;
}

test("AI drafts, teacher approves, student reviews then takes the quiz with HABIT AI", async ({ page }, info) => {
  test.setTimeout(240_000);
  const n = info.project.name;

  // ---- teacher
  await login(page, "gv.dia@preclass.local");
  await page.goto("/plans");
  await page.setInputFiles("#plan-file", path.join(import.meta.dirname, "fixtures", "plan-ai.docx"));
  await page.getByRole("button", { name: "Đọc giáo án" }).click();
  await expect(page.getByRole("heading", { name: "CHỦ ĐỀ MẪU" })).toBeVisible({ timeout: 90_000 });
  const planId = page.url().split("/plans/")[1]!.split(/[?#]/)[0]!;
  await expect(page.getByRole("heading", { name: "AI soạn từ giáo án" })).toBeVisible();
  await expect(page.getByText(/câu AI soạn, \d+ cần xác nhận/)).toBeVisible({ timeout: 60_000 }); // "Đang soạn…" turns into the count
  await page.screenshot({ path: shot("drafts", n), fullPage: n !== "webkit-390" });

  const quiz = page.getByRole("article", { name: "Câu hỏi AI soạn" });
  expect(await quiz.count()).toBeGreaterThanOrEqual(5);
  await expect(quiz.first().getByText("AI soạn", { exact: true })).toBeVisible();
  await expect(quiz.first().getByText("Trích từ giáo án")).toBeVisible();
  await expect(quiz.first().getByRole("button", { name: "Sửa" })).toBeVisible();
  await expect(quiz.first().getByRole("button", { name: "Loại" })).toBeVisible();
  const stems: string[] = [];
  for (const i of [0, 1]) {
    stems.push((await quiz.nth(i).locator("strong").first().innerText()).trim());
    await quiz.nth(i).getByRole("button", { name: "Duyệt" }).click();
    await expect(quiz.nth(i).getByText("Đã duyệt")).toBeVisible();
  }
  await page.getByRole("tab", { name: /Ôn tập/ }).click();
  const cards = page.getByRole("article", { name: "Thẻ ôn AI soạn" });
  expect(await cards.count()).toBeGreaterThanOrEqual(4);
  for (const i of [0, 1, 2]) {
    await cards.nth(i).getByRole("button", { name: "Duyệt" }).click();
    await expect(cards.nth(i).getByText("Đã duyệt")).toBeVisible();
  }
  await page.getByRole("button", { name: "Tạo bài chuẩn bị trước giờ học" }).click();
  await expect(page).toHaveURL(/\/lessons\/.+tab=editor/, { timeout: 60_000 });
  const lessonId = page.url().split("/lessons/")[1]!.split(/[?#]/)[0]!;

  // review every block, publish and assign through the API (the lesson workspace has its own e2e specs)
  const lesson = await ok<{ currentRevision: { id: string; version: number } }>(await page.request.get(`/v1/lessons/${lessonId}`));
  const rev = lesson.currentRevision.id;
  const blocks = (await ok<{ items: { id: string; contentHash: string; kind: string }[] }>(await page.request.get(`/v1/revisions/${rev}/blocks`))).items;
  expect(blocks.filter((b) => b.kind === "review_card")).toHaveLength(3);
  for (const b of blocks) await ok(await page.request.post(`/v1/blocks/${b.id}/reviews`, { headers: H, data: { action: "APPROVE", contentHash: b.contentHash } }));
  const pub = await ok<{ id: string }>(
    await page.request.post(`/v1/revisions/${rev}/publish`, { headers: H, data: { confirmChecked: true, version: lesson.currentRevision.version } }),
  );
  const classes = await ok<{ items: { id: string; code: string }[] }>(await page.request.get("/v1/classes"));
  const klass = classes.items.find((c) => c.code === "10A1")!;
  const asg = await ok<{ id: string }>(
    await page.request.post(`/v1/published/${pub.id}/assignments`, {
      headers: H,
      data: { classId: klass.id, openAt: "2020-01-01T00:00:00+07:00", dueAt: "2099-01-01T00:00:00+07:00" },
    }),
  );
  expect(planId).toBeTruthy();
  await page.request.post("/v1/auth/logout", { headers: H });

  // ---- student: review first
  await login(page, STUDENT[n] ?? "HS10-08");
  await page.goto(`/student/assignments/${asg.id}`);
  await expect(page.getByRole("heading", { name: "Em đã học bài này chưa?" })).toBeVisible({ timeout: 30_000 });
  await expect(page.locator("section.item")).toHaveCount(0); // the quiz stays closed until the student chooses
  await page.screenshot({ path: shot("ask", n) });
  await page.getByRole("button", { name: "Chưa, ôn trước" }).click();
  await expect(page.getByText("1. Ôn nhanh")).toHaveAttribute("aria-current", "step");
  await expect(page.getByText("Thẻ 1/3 · không tính điểm")).toBeVisible();
  await page.getByRole("button", { name: "Đúng", exact: true }).click(); // self-check: explanation at once, no score
  await expect(page.getByText(/Đúng rồi|Chưa đúng/)).toBeVisible();
  await page.getByRole("button", { name: "Thẻ tiếp" }).click();
  await expect(page.getByText("Thẻ 2/3 · không tính điểm")).toBeVisible();
  await page.screenshot({ path: shot("review", n) });
  await page.getByRole("button", { name: "Đủ rồi, làm bài" }).click();
  await expect(page.getByText("2. Làm bài kiểm tra")).toHaveAttribute("aria-current", "step");
  await expect(page.getByRole("button", { name: "Xem lại phần ôn" })).toBeVisible();
  for (const s of stems) await expect(page.locator("section.item").filter({ hasText: s })).toBeVisible();
  await page.screenshot({ path: shot("quiz", n), fullPage: n !== "webkit-390" });

  // ---- HABIT AI: five questions are not blocked, and "I have not studied" points to a review card
  const item = page.locator("section.item").filter({ hasText: stems[0]! });
  await item.getByRole("button", { name: "Hỏi HABIT AI" }).click();
  const sheet = page.getByRole("dialog", { name: "Hỏi HABIT AI" });
  await expect(sheet).toBeVisible();
  const asks = ["dân cư là gì", "em cần số liệu nào", "đọc đề thế nào", "cảm ơn nhé", "em chưa học bài, em nên bắt đầu từ đâu"];
  for (const [i, q] of asks.entries()) {
    const res = page.waitForResponse((r) => r.url().includes("/chat") && r.request().method() === "POST");
    await sheet.getByLabel("Câu hỏi cho HABIT AI").fill(q);
    await sheet.getByRole("button", { name: "Gửi" }).click();
    expect((await res).status(), `message ${i + 1}`).toBe(200);
  }
  await expect(sheet.locator(".habit-msg.me")).toHaveCount(5);
  await expect(sheet.getByText("Hôm nay em hỏi nhiều rồi")).toHaveCount(0);
  await sheet.getByRole("button", { name: "Mở thẻ ôn" }).click(); // closes the sheet and opens the matching card
  await expect(sheet).toBeHidden();
  await expect(page.getByText(/Thẻ \d\/3 · không tính điểm/)).toBeVisible();
  await page.getByRole("button", { name: /làm bài/ }).first().click();
  await expect(page.getByText("2. Làm bài kiểm tra")).toHaveAttribute("aria-current", "step");

  // ---- hints go up to 10/10, never blocked by the chat limit
  const q1 = page.locator("section.item").filter({ hasText: stems[0]! });
  for (let k = 1; k <= 10; k++) {
    await q1.getByRole("button", { name: `Gợi ý ${k}/10`, exact: true }).click();
    await expect(q1.locator(".habit-hint")).toHaveCount(k, { timeout: 20_000 });
  }
  await expect(q1.getByRole("button", { name: "Gợi ý 10/10 (đã dùng hết)" })).toBeDisabled();
  await expect(q1.locator(".habit-hint").first().locator("p")).not.toBeEmpty();
  await page.screenshot({ path: shot("hints-10", n), fullPage: n !== "webkit-390" });
});
