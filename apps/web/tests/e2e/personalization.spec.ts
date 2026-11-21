import { expect, test } from "@playwright/test";
import { expectNoHorizontalScroll, login } from "./helpers";

// One student per project (preferences persist). Needs the API with CHAT_ENABLED=true and PERSONALIZATION_ENABLED=true.
const STUDENT: Record<string, string> = { "mobile-390": "HS10-01", "tablet-768": "HS10-02", "desktop-1280": "HS10-03", "webkit-390": "HS10-04" };
const shot = (name: string, project: string) => `test-results/personalization/${name}-${project}.png`;

test("student picks options, uses focus mode with a timer, and the choices persist", async ({ page }, info) => {
  await login(page, STUDENT[info.project.name] ?? "HS10-05");
  await page.locator(".assignment-card").first().click();
  await expect(page.locator("section.item").first()).toBeVisible({ timeout: 30_000 });

  await page.getByText("Em muốn học theo cách nào hôm nay?").click();
  await expect(page.getByLabel("Chia nhỏ từng bước")).not.toBeChecked(); // default: off
  await page.getByLabel("Chia nhỏ từng bước").check();
  await page.getByLabel("Nhắc tiến độ").check();
  await page.getByLabel("Hẹn giờ tập trung").selectOption("10");
  await expect(page.getByRole("status").filter({ hasText: "Em đã làm 0/2 câu" })).toBeVisible();
  await page.screenshot({ path: shot("options", info.project.name), fullPage: true });
  await expectNoHorizontalScroll(page);

  await page.getByRole("button", { name: "Chế độ tập trung" }).click();
  const focus = page.getByRole("region", { name: "Chế độ tập trung" });
  await expect(focus.getByText("Câu 1/2")).toBeVisible();
  await expect(focus.getByRole("timer")).toContainText("09:5");
  await expect(page.locator("section.item")).toHaveCount(1); // one question per screen
  await expect(page.getByRole("region", { name: "Thói quen học của em" })).toHaveCount(0); // secondary parts hidden
  await focus.getByRole("button", { name: "Gợi ý 1/3" }).click();
  const hint = focus.locator(".habit-hint").first();
  await expect(hint).toBeVisible();
  expect((await hint.innerText()).length).toBeLessThan(160); // "chia nhỏ": one short sentence
  await page.screenshot({ path: shot("focus", info.project.name), fullPage: true });
  await focus.getByRole("button", { name: "Câu tiếp" }).click();
  await expect(focus.getByText("Câu 2/2")).toBeVisible();

  // Choices persist across a reload; focus mode is per visit.
  await page.reload();
  await expect(page.locator("section.item").first()).toBeVisible({ timeout: 30_000 });
  await page.getByText("Em muốn học theo cách nào hôm nay?").click();
  await expect(page.getByLabel("Chia nhỏ từng bước")).toBeChecked();
  await expect(page.getByLabel("Hẹn giờ tập trung")).toHaveValue("10");
  await page.getByRole("button", { name: "Tắt hết" }).click();
  await expect(page.getByLabel("Chia nhỏ từng bước")).not.toBeChecked();
  await expect(page.getByLabel("Hẹn giờ tập trung")).toHaveValue("off");
});
