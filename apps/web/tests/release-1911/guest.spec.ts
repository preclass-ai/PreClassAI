import { expect, test, type Page } from "@playwright/test";

/** Anonymous survey access. Skipped when the target API has GUEST_ACCESS_ENABLED=false. Run on projects 390 and webkit. */
const CODE = /KS-[A-HJ-NP-Z2-9]{4}/;

test.beforeEach(async ({ request }) => {
  const cfg = await request.get("/v1/auth/config");
  test.skip(!cfg.ok() || !(await cfg.json()).guestEnabled, "guest access is off on this API");
});

async function enter(page: Page) {
  await page.goto("/login");
  await expect(page.getByText("Không thu tên hay email")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Vào làm thử (không cần tài khoản)" }).click();
  await expect(page.getByRole("heading", { name: "Bài được giao" })).toBeVisible({ timeout: 30_000 });
  const banner = page.locator(".guest-banner");
  await expect(banner).toContainText(CODE);
  return ((await banner.innerText()).match(CODE) ?? [""])[0];
}

test("guest: enter, answer 2 questions, see explanations and the survey code", async ({ page }) => {
  const code = await enter(page);
  await page.locator(".assignment-card").first().click();
  await expect(page).toHaveURL(/\/student\/assignments\//);
  for (let i = 0; i < 2; i++) {
    const item = page.locator("section.item").nth(i);
    await item.getByRole("button", { name: "Nộp câu trả lời" }).waitFor({ timeout: 30_000 });
    await expect(item.locator(".explanation")).toHaveCount(0); // PR-08: nothing before answering
    if (await item.locator(".option").count()) await item.locator(".option").first().click();
    else if (await item.getByLabel("Đáp số").count()) await item.getByLabel("Đáp số").fill("10");
    else await item.getByLabel("Câu trả lời").fill("Trả lời thử.");
    await item.getByRole("button", { name: "Nộp câu trả lời" }).click();
    await expect(item.getByRole("status")).toContainText(/Đúng|Chưa đúng/, { timeout: 30_000 });
    await expect(item.locator(".explanation")).not.toBeEmpty();
  }
  await expect(page.locator(".guest-banner")).toContainText(code);
  await expect(page.locator(".guest-survey")).toContainText(code); // end-of-worksheet card
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
  const r = await page.request.get("/v1/lessons");
  expect([403, 404]).toContain(r.status()); // not a teacher
});

test("guest: a second private window is a different guest; the first can come back with its code", async ({ page, browser }) => {
  const first = await enter(page);
  const other = await browser.newContext();
  try {
    const page2 = await other.newPage();
    const second = await enter(page2);
    expect(second).not.toBe(first);
  } finally {
    await other.close();
  }
  // lost cookie: resume with the code
  await page.context().clearCookies();
  await page.goto("/login");
  await page.getByText("Đã có mã khảo sát?").click();
  await page.getByLabel("Mã khảo sát").fill(first.toLowerCase());
  await page.getByRole("button", { name: "Vào lại bằng mã" }).click();
  await expect(page.locator(".guest-banner")).toContainText(first, { timeout: 30_000 });
});

test("guest: /thu?bai=dan-so-vung opens the lesson directly", async ({ page }) => {
  await page.goto("/thu?bai=dan-so-vung");
  await expect(page).toHaveURL(/\/student\/assignments\//, { timeout: 30_000 });
  await expect(page.locator(".guest-banner")).toContainText(CODE);
  await expect(page.locator("section.item").first()).toBeVisible({ timeout: 30_000 });
});

test("guest: a brand-new guest sees only the seed lessons, never an [E2E] test lesson", async ({ page }) => {
  await enter(page);
  const r = await page.request.get("/v1/student/assignments");
  expect(r.ok()).toBeTruthy();
  const titles = ((await r.json()).items as { title: string }[]).map((i) => i.title);
  expect(titles.filter((t) => t.startsWith("[E2E]")), "test lessons must stay in the private E2E class").toEqual([]);
  expect(titles).toEqual(["Phân bố dân cư theo vùng"]); // the seed's one published lesson
});
