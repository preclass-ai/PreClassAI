import { expect, test } from "@playwright/test";
import { login } from "./helpers";

// HABIT AI bottom sheet on real phone viewports (iPhone 13, iPhone SE, Pixel 7). Needs the API with CHAT_ENABLED=true.
// Regression: the sheet had only a max-height, so the message list (flex 1 1 0) collapsed to a thin strip.
const STUDENT: Record<string, string> = { "device-iphone-13": "HS10-05", "device-iphone-se": "HS10-06", "device-pixel-7": "HS10-07" };
const shot = (name: string, project: string) => `test-results/habit-mobile/${name}-${project}.png`;

test("HABIT AI sheet on a phone: messages are readable, last message in view, chips scroll sideways", async ({ page }, info) => {
  const n = info.project.name;
  await login(page, STUDENT[n] ?? "HS10-08");
  await page.locator(".assignment-card").first().click();
  const item = page.locator("section.item").first();
  await expect(item).toBeVisible({ timeout: 30_000 });
  await item.getByRole("button", { name: "Hỏi HABIT AI" }).click();
  const sheet = page.getByRole("dialog", { name: "Hỏi HABIT AI" });
  await expect(sheet).toBeVisible();
  await expect(sheet).toHaveAttribute("aria-modal", "true");

  // BEFORE: the old rule (max-height only) reproduced in place, for the report
  const fix = await page.addStyleTag({ content: ".habit-sheet{height:auto!important;max-height:min(80dvh,var(--vvh,80dvh))!important}" });
  const vp = page.viewportSize()!;
  const log = sheet.locator(".habit-log");
  const thin = (await log.boundingBox())!.height;
  await page.screenshot({ path: shot("before", n) });
  await fix.evaluate((el) => (el as Element).remove());

  for (const q of ["dân cư là gì", "em cần số liệu nào", "cảm ơn nhé"]) {
    const res = page.waitForResponse((r) => r.url().includes("/chat") && r.request().method() === "POST");
    await sheet.getByLabel("Câu hỏi cho HABIT AI").fill(q);
    await sheet.getByRole("button", { name: "Gửi" }).click();
    await res;
  }
  await expect(sheet.locator(".habit-msg.me")).toHaveCount(3);

  const box = (await sheet.boundingBox())!;
  expect(box.height).toBeLessThanOrEqual(vp.height * 0.85 + 1);
  expect(box.height).toBeGreaterThanOrEqual(vp.height * 0.6); // a real sheet, not a strip
  const logBox = (await log.boundingBox())!;
  expect(logBox.height, `message area ${logBox.height}px (was ${thin}px before the fix)`).toBeGreaterThanOrEqual(vp.height * 0.4);

  const last = (await sheet.locator(".habit-turn, .habit-msg").last().boundingBox())!;
  expect(last.y + last.height).toBeLessThanOrEqual(logBox.y + logBox.height + 1); // newest message inside the scroll area
  expect(last.y + last.height).toBeLessThanOrEqual(vp.height); // and inside the viewport
  expect(await log.evaluate((el) => el.scrollHeight - el.scrollTop - el.clientHeight)).toBeLessThanOrEqual(2); // scrolled to the end

  // input: reachable above the safe area, 16px font (no iOS zoom)
  const input = sheet.getByLabel("Câu hỏi cho HABIT AI");
  const ib = (await input.boundingBox())!;
  expect(ib.y + ib.height).toBeLessThanOrEqual(vp.height);
  expect(await input.evaluate((el) => parseFloat(getComputedStyle(el).fontSize))).toBeGreaterThanOrEqual(16);

  // chips scroll sideways and snap
  const chips = sheet.locator(".habit-chips");
  const m = await chips.evaluate((el) => ({ sw: el.scrollWidth, cw: el.clientWidth, ox: getComputedStyle(el).overflowX, snap: getComputedStyle(el).scrollSnapType }));
  expect(m.ox).toBe("auto");
  expect(m.snap).toContain("x");
  expect(m.sw).toBeGreaterThan(m.cw);
  await chips.evaluate((el) => el.scrollBy({ left: 120 }));
  await expect.poll(() => chips.evaluate((el) => el.scrollLeft)).toBeGreaterThan(0);

  // page behind does not scroll while the sheet is open
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).overflow)).toBe("hidden");
  await page.screenshot({ path: shot("after", n) });

  await sheet.getByRole("button", { name: "Đóng HABIT AI" }).click();
  await expect(sheet).toBeHidden();
  expect(await page.evaluate(() => getComputedStyle(document.documentElement).overflow)).not.toBe("hidden");
});
