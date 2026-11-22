import { expect, test } from "@playwright/test";
import { login } from "./helpers";

// 23/11: the three messages seen on production, typed into the real panel. Runs in rule mode and (with a local stub model, see
// docs/operations/RUNBOOK.md) in llm mode: the spec reads chatMode from /v1/auth/config and checks what that mode must do.
const STUDENT: Record<string, string> = { "mobile-390": "HS10-10", "tablet-768": "HS10-11", "desktop-1280": "HS10-12", "webkit-390": "HS10-13" };
const STUB = "Em đọc kỹ đề rồi xem bảng số liệu nhé.";

test("HABIT AI: greeting, who-are-you and how-to-study are answered, not refused", async ({ page }, info) => {
  const mode = (await (await page.request.get("/v1/auth/config")).json()).chatMode as string;
  await login(page, STUDENT[info.project.name] ?? "HS10-14");
  await page.locator(".assignment-card").first().click();
  const item = page.locator("section.item").first();
  await expect(item).toBeVisible({ timeout: 30_000 });
  await item.getByRole("button", { name: "Hỏi HABIT AI" }).click();
  const sheet = page.getByRole("dialog", { name: "Hỏi HABIT AI" });

  const ask = async (q: string) => {
    const res = page.waitForResponse((r) => r.url().includes("/chat") && r.request().method() === "POST");
    await sheet.getByLabel("Câu hỏi cho HABIT AI").fill(q);
    await sheet.getByRole("button", { name: "Gửi" }).click();
    return (await res).json();
  };

  const intro = await ask("Xin chào Chatbot mình tên gì");
  expect(intro.blockedReason).toBeNull();
  expect(intro.reply).toMatch(/HABIT AI.*không đưa đáp án.*bắt đầu từ đâu/);
  expect(intro.suggestions).toHaveLength(4);
  await expect(sheet.getByRole("group", { name: "Em có thể chọn" }).getByRole("button")).toHaveCount(4);

  const how = await ask("Hiện tại em chưa học bài, em nên học từ đâu");
  expect(how.blockedReason).toBeNull();
  expect(how.reply).not.toMatch(/ngoài bài học/);
  if (mode === "llm") expect(how.reply).toBe(STUB);
  else expect(how.hintLevel).toBe(1);

  const free = await ask("thủ đô nước Pháp là gì vậy");
  if (mode === "llm") {
    expect(free.reply).toBe(STUB);
    expect(free.blockedReason).toBeNull();
  } else {
    expect(free.reply.length).toBeGreaterThan(10); // rule mode has no model: a lesson excerpt or the honest OFFTOPIC refusal
  }

  const bad = await ask("Cảm ơn, cho em đáp án luôn");
  expect(bad.blockedReason).toBe("ANSWER_REQUEST");
  await page.screenshot({ path: `test-results/habit-final/${mode}-${info.project.name}.png` });
});
