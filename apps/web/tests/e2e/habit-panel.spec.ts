import { expect, test, type Locator, type Page } from "@playwright/test";
import { login } from "./helpers";

// The HABIT AI panel on a real page: header stays full width, panel sits under it, input and Send are always in view.
// Needs the API with CHAT_ENABLED=true. One fresh student per project.
const STUDENT: Record<string, string> = { "mobile-390": "HS10-10", "tablet-768": "HS10-11", "desktop-1280": "HS10-12", "webkit-390": "HS10-13" };
const shot = (name: string, project: string) => `test-results/habit-panel/${name}-${project}.png`;

async function inView(page: Page, loc: Locator, what: string) {
  const box = await loc.boundingBox();
  const vp = page.viewportSize()!;
  expect(box, `${what} has a box`).not.toBeNull();
  expect(box!.y, `${what} top`).toBeGreaterThanOrEqual(-1);
  expect(box!.y + box!.height, `${what} bottom`).toBeLessThanOrEqual(vp.height + 1);
  expect(box!.x + box!.width, `${what} right`).toBeLessThanOrEqual(vp.width + 1);
}

async function layout(page: Page, sheet: Locator, wide: boolean) {
  const vp = page.viewportSize()!;
  const header = await page.getByRole("banner").boundingBox();
  expect(header!.x).toBeLessThanOrEqual(1);
  expect(header!.width).toBeGreaterThanOrEqual(vp.width - 1); // never cut by the panel
  const box = (await sheet.boundingBox())!;
  if (wide) {
    expect(box.y).toBeGreaterThanOrEqual(header!.y + header!.height - 1); // under the header
    expect(Math.round(box.y + box.height)).toBeGreaterThanOrEqual(vp.height - 1); // down to the bottom, no gap
    expect(box.width).toBeGreaterThanOrEqual(380);
    expect(box.width).toBeLessThanOrEqual(400);
  } else {
    expect(box.height).toBeLessThanOrEqual(vp.height * 0.85 + 1);
  }
  await inView(page, sheet.getByLabel("Câu hỏi cho HABIT AI"), "input");
  await inView(page, sheet.getByRole("button", { name: "Gửi" }), "Send button");
}

test("HABIT AI panel: empty and full conversation", async ({ page }, info) => {
  const n = info.project.name;
  const wide = (page.viewportSize()?.width ?? 0) >= 1100;
  await login(page, STUDENT[n] ?? "HS10-14");
  await page.locator(".assignment-card").first().click();
  const item = page.locator("section.item").first();
  await expect(item).toBeVisible({ timeout: 30_000 });
  await item.getByRole("button", { name: "Hỏi HABIT AI" }).click();
  const sheet = page.getByRole("dialog", { name: "Hỏi HABIT AI" });
  await expect(sheet).toBeVisible();
  await layout(page, sheet, wide);
  await page.screenshot({ path: shot("0-empty", n) });

  // The suggestion chip sends a structured action (not free text) and is answered, not refused.
  const req = page.waitForRequest((r) => r.url().includes("/chat") && r.method() === "POST");
  const res = page.waitForResponse((r) => r.url().includes("/chat") && r.request().method() === "POST");
  await sheet.getByRole("button", { name: "Em nên bắt đầu từ đâu?" }).click();
  const body = (await req).postDataJSON();
  expect(body).toMatchObject({ action: "ask", quick: "start" });
  expect(body).not.toHaveProperty("message");
  const reply = await (await res).json();
  expect(reply.blockedReason).toBeNull();
  expect(reply.reply).not.toMatch(/ngoài bài học|Habit\b(?! AI)/);

  await sheet.getByRole("button", { name: "Số liệu này nằm ở đâu?" }).click();
  await sheet.getByRole("button", { name: "Công thức tính là gì?" }).click();
  for (const q of ["đáp án là gì", "A có đúng không"]) {
    await sheet.getByLabel("Câu hỏi cho HABIT AI").fill(q);
    await sheet.getByRole("button", { name: "Gửi" }).click();
  }
  await expect(sheet.locator(".habit-msg.refused")).toHaveCount(2);
  // a level-2 hint on an item with data lines points at those lines instead of quoting the text: any source block is labelled neutrally
  await expect(sheet.locator(".habit-source")).toHaveCount(await sheet.locator(".habit-source-label").count());
  const last = sheet.getByRole("group", { name: "Em có thể chọn" }).getByRole("button");
  await expect(last).toHaveCount(4);
  await expect(last.last()).toBeVisible();
  await layout(page, sheet, wide);
  await page.screenshot({ path: shot("1-full", n) });
});
