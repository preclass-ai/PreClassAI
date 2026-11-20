import { appendFileSync, mkdirSync } from "node:fs";
import { E2E_MODE, openAccountForm, passwordFor } from "../e2e/helpers";
import { expect, test, type Page } from "@playwright/test";

// Student flow on the SEEDED published lesson (no publish/assign). Env: STUDENT_<vp> ids, BLOCK_ID.
const DIR = "test-results/release-1911";
const STUDENT: Record<string, string> = { "390": "HS10-12", "768": "HS10-14", "1280": "HS10-13", webkit: "HS10-15" };

function rec(o: object) {
  mkdirSync(DIR, { recursive: true });
  appendFileSync(`${DIR}/results.jsonl`, JSON.stringify(o) + "\n");
}

async function noHScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
}

test.skip(E2E_MODE, "seed students have no password on the cloud demo: guest.spec covers the seed lesson");
test("seeded: student answers 2 questions, sees explanation, provenance blocked", async ({ page }, info) => {
  const vp = info.project.name;
  const errs: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" && !(m.location().url.includes("/v1/me") && /401/.test(m.text()))) errs.push(m.text().slice(0, 150));
  });
  let step = "login";
  try {
    await page.goto("/login");
    await openAccountForm(page);
    await page.getByLabel("Email hoặc mã học sinh").fill(STUDENT[vp]!);
    await page.getByLabel("Mật khẩu").fill(passwordFor(STUDENT[vp]!));
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page.getByRole("heading", { name: "Bài được giao" })).toBeVisible({ timeout: 30_000 });
    await noHScroll(page);
    rec({ vp, check: "load-student-ms", ms: await page.evaluate(() => Math.round((performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming).loadEventEnd)) });
    await page.screenshot({ path: `${DIR}/seed-${vp}-01-home.png`, fullPage: true });

    step = "answer";
    await page.locator(".assignment-card").first().click();
    await expect(page).toHaveURL(/\/student\/assignments\//);
    for (let i = 0; i < 2; i++) {
      const item = page.locator("section.item").nth(i);
      await item.getByRole("button", { name: "Nộp câu trả lời" }).waitFor({ timeout: 30_000 });
      await expect(item.locator(".explanation")).toHaveCount(0);
      if (await item.locator(".option").count()) await item.locator(".option").first().click();
      else if (await item.getByLabel("Đáp số").count()) await item.getByLabel("Đáp số").fill("10");
      else await item.getByLabel("Câu trả lời").fill("Trả lời thử cho kiểm thử phát hành.");
      await item.getByRole("button", { name: "Nộp câu trả lời" }).click();
      await expect(item.getByRole("status")).toContainText(/Đúng|Chưa đúng/, { timeout: 30_000 });
      await expect(item.locator(".explanation")).not.toBeEmpty();
    }
    await noHScroll(page);
    await page.screenshot({ path: `${DIR}/seed-${vp}-02-answered.png`, fullPage: true });

    step = "provenance";
    const r = await page.request.get(`/v1/blocks/${process.env.BLOCK_ID ?? "00000000-0000-0000-0000-000000000000"}/provenance`);
    rec({ vp, check: "student-provenance-status", status: r.status() });
    expect(r.status()).toBe(404); // PR-08
    rec({ vp, step: "seeded-student-flow", student: STUDENT[vp], ok: true, consoleErrors: errs.length, sample: errs.slice(0, 2) });
  } catch (e) {
    await page.screenshot({ path: `${DIR}/FAIL-seed-${vp}.png`, fullPage: true }).catch(() => undefined);
    rec({ vp, step: "seeded-student-flow", student: STUDENT[vp], ok: false, failedAt: step, err: String(e).slice(0, 250) });
    throw e;
  }
});
