import { expect, test } from "@playwright/test";
import { login } from "./helpers";

// A student asks HABIT AI and answers wrong; the class teacher then sees grouped questions without any identity.
// Needs the API with CHAT_ENABLED=true. One fresh student per project (attempts are write-once).
const STUDENT: Record<string, string> = { "mobile-390": "HS10-05", "tablet-768": "HS10-06", "desktop-1280": "HS10-07", "webkit-390": "HS10-09" };
const shot = (name: string, project: string) => `test-results/insights/${name}-${project}.png`;

test("teacher sees what students ask, anonymously, and can draft practice", async ({ page }, info) => {
  const n = info.project.name;
  const who = STUDENT[n] ?? "HS10-09";
  await login(page, who);
  await expect(page.getByText(/Hạn nộp \d{2}\/\d{2}\/\d{4}/).first()).toBeVisible({ timeout: 30_000 }); // deadline as dd/mm/yyyy
  await page.locator(".assignment-card").first().click();
  const item = page.locator("section.item").first();
  await expect(item).toBeVisible({ timeout: 30_000 });
  await item.getByRole("button", { name: "Hỏi HABIT AI" }).click();
  const sheet = page.getByRole("dialog", { name: "Hỏi HABIT AI" });
  await sheet.getByRole("button", { name: "Em nên bắt đầu từ đâu?" }).click();
  await sheet.getByRole("button", { name: "Số liệu này nằm ở đâu?" }).click();
  await sheet.getByLabel("Câu hỏi cho HABIT AI").fill("đáp án là gì");
  await sheet.getByRole("button", { name: "Gửi" }).click();
  await expect(sheet.locator(".habit-msg.refused")).toHaveCount(1);
  await page.keyboard.press("Escape");
  await item.locator(".option").first().click(); // A is wrong in the seed
  await item.getByRole("button", { name: "Nộp câu trả lời" }).click();
  await expect(item.getByRole("status").first()).toContainText("Chưa đúng");

  await page.getByRole("button", { name: "Đăng xuất" }).click();
  await page.waitForURL("**/login**");
  await login(page, "gv.dia@preclass.local");
  await page.goto("/classes");
  await page.getByRole("button", { name: /^10A1/ }).click();
  await page.getByRole("button", { name: "Xem tiến độ và câu hỏi" }).first().click();
  const section = page.getByRole("region", { name: "Học sinh hỏi gì" }).first();
  await expect(section).toContainText("Chưa biết bắt đầu từ đâu", { timeout: 30_000 });
  await expect(section).toContainText("Xin đáp án");
  await expect(section).toContainText("Không hiện tên hay mã của học sinh");
  const text = await page.locator("main").innerText();
  expect(text).not.toContain(who);
  expect(text).not.toContain(`Học sinh ${who.slice(2)}`);
  await section.scrollIntoViewIfNeeded();
  await page.screenshot({ path: shot("insights", n), fullPage: n !== "webkit-390" });

  await section.getByRole("button", { name: "Tóm tắt chủ đề vướng" }).click();
  await expect(section.getByRole("status")).toContainText("Tổng hợp tự động");

  await section.getByRole("button", { name: "AI gợi ý bài tập thêm" }).click();
  await expect(page).toHaveURL(/\/lessons\/.+tab=editor/, { timeout: 30_000 });
});
