import { appendFileSync, mkdirSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

const DIR = "test-results/release-1911";
const PASSWORD = process.env.SEED_PASSWORD ?? "preclass-demo";
const STUDENT: Record<string, string> = { "390": "HS10-03", "768": "HS10-04", "1280": "HS10-05", webkit: "HS10-06" };
const TEXT =
  "Số dân các vùng (DỮ LIỆU MINH HỌA)\n\nDân cư phân bố không đều giữa các vùng.\n\n" +
  "| Vùng | Số dân (triệu người) |\n|---|---|\n| Đồng bằng sông Hồng | 23,2 |\n| Tây Nguyên | 5,9 |\n" +
  "| Đông Nam Bộ | 17,8 |\n| Duyên hải miền Trung | 9,4 |";

test.describe.configure({ mode: "serial" });
const st = { title: "", lessonUrl: "", assignmentUrl: "", blockId: "" };
let n = 0;

function rec(o: object) {
  mkdirSync(DIR, { recursive: true });
  appendFileSync(`${DIR}/results.jsonl`, JSON.stringify(o) + "\n");
}

/** Run one named step: record ok/fail + screenshot (also on failure), rethrow so the viewport stops at the first failure. */
async function S(page: Page, vp: string, name: string, fn: () => Promise<unknown>) {
  mkdirSync(DIR, { recursive: true });
  const t0 = Date.now();
  const file = `${vp}-${String(++n).padStart(2, "0")}-${name.replace(/\W+/g, "-")}.png`;
  try {
    await fn();
    await page.screenshot({ path: `${DIR}/${file}`, fullPage: true });
    rec({ vp, step: name, ok: true, ms: Date.now() - t0 });
  } catch (e) {
    await page.screenshot({ path: `${DIR}/FAIL-${file}`, fullPage: true }).catch(() => undefined);
    rec({ vp, step: name, ok: false, err: String(e).slice(0, 300) });
    throw e;
  }
}

async function login(page: Page, id: string) {
  await page.goto("/login");
  await page.getByLabel("Email hoặc mã học sinh").fill(id);
  await page.getByLabel("Mật khẩu").fill(PASSWORD);
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).not.toHaveURL(/\/login/, { timeout: 30_000 });
}

async function noHScroll(page: Page) {
  expect(await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
}

const loadMs = (page: Page) =>
  page.evaluate(() => Math.round((performance.getEntriesByType("navigation")[0] as PerformanceNavigationTiming).loadEventEnd));

async function approveAll(page: Page) {
  // On mobile the block inspector is a bottom sheet that covers the tabs.
  if (await page.locator(".editor-inspector.open").count()) await page.getByRole("button", { name: "Đóng" }).click();
  await page.getByRole("tab", { name: "Duyệt" }).click();
  const approve = page.getByRole("button", { name: "Duyệt khối này" });
  await expect(approve.first()).toBeVisible({ timeout: 30_000 });
  for (let i = 0, idle = 0; i < 80 && idle < 2; i++) {
    if ((await approve.count()) === 0) {
      // A refetch can briefly empty the list: only stop after it stays empty once the network is quiet.
      await page.waitForLoadState("networkidle");
      idle++;
      continue;
    }
    idle = 0;
    const before = await approve.count();
    await approve.first().click();
    await expect(approve).toHaveCount(before - 1);
  }
}

async function publishAssign(page: Page, vp: string) {
  await page.getByRole("tab", { name: /Xuất bản/ }).click();
  await expect(page.locator(".checklist li").first()).toBeVisible({ timeout: 30_000 });
  if (await page.locator(".checklist li.fail").count()) {
    // Kept as a detector: with gcTime 0 on the gate query this should no longer happen.
    // Observed: gate shown stale right after the last approval (API says canPublish=true). Reload and carry on.
    rec({ vp, check: "stale-gate-after-last-approval", stale: true });
    await page.reload();
    await expect(page.locator(".checklist li").first()).toBeVisible({ timeout: 30_000 });
  }
  await expect(page.locator(".checklist li.fail")).toHaveCount(0);
  await page.getByText("Tôi đã đọc từng khối").click();
  await page.getByRole("button", { name: "Xuất bản", exact: true }).click({ timeout: 20_000 });
  await expect(page.getByText(/đã xuất bản\./)).toBeVisible({ timeout: 30_000 });
  const sel = page.locator("select").filter({ has: page.locator("option", { hasText: "10A1" }) });
  if (await sel.count()) {
    const label = (await sel.first().locator("option", { hasText: "10A1" }).first().innerText()).trim();
    await sel.first().selectOption({ label });
  }
  await page.getByRole("button", { name: "Giao bài" }).click();
  await expect(page.getByText(/Đã giao cho lớp/)).toBeVisible({ timeout: 30_000 });
}

const cnt = { prov: 0, s5xx: 0, s429: 0 };
function watch(page: Page, errs: string[], badCsrf?: string[]) {
  page.on("response", (r) => {
    if (r.url().includes("/provenance") && r.request().method() === "GET") cnt.prov++;
    if (r.status() >= 500) cnt.s5xx++;
    if (r.status() === 429) cnt.s429++;
  });
  page.on("console", (m) => {
    if (m.type() === "error" && !(m.location().url.includes("/v1/me") && /401/.test(m.text()))) errs.push(m.text().slice(0, 150));
  });
  if (badCsrf)
    page.on("request", (r) => {
      if (r.url().includes("/v1/") && r.method() !== "GET" && r.headers()["x-preclass-csrf"] !== "1") badCsrf.push(`${r.method()} ${r.url()}`);
    });
}

test("T1 teacher: login, source, generate, edit, review, publish, assign, history", async ({ page, context }, info) => {
  const vp = info.project.name;
  Object.assign(cnt, { prov: 0, s5xx: 0, s429: 0 });
  st.title = `Release ${vp} ${Date.now().toString(36)}`;
  const errs: string[] = [];
  const badCsrf: string[] = [];
  watch(page, errs, badCsrf);

  await S(page, vp, "login", async () => {
    await login(page, "gv.dia@preclass.local");
    await expect(page).toHaveURL(/\/lessons$/);
    await noHScroll(page);
    const ck = (await context.cookies()).find((c) => c.name === "preclass_session");
    expect(ck, "session cookie").toBeTruthy();
    rec({ vp, check: "cookie", secure: ck!.secure, httpOnly: ck!.httpOnly, sameSite: ck!.sameSite });
    rec({ vp, check: "load-lessons-ms", ms: await loadMs(page) });
  });
  await S(page, vp, "S01-source", async () => {
    await page.getByRole("link", { name: "Nguồn", exact: true }).click();
    await expect(page.getByRole("heading", { name: "Thư viện nguồn" })).toBeVisible();
    await page.getByRole("button", { name: "Thêm nguồn" }).click();
    await page.getByLabel("Tên nguồn").fill(st.title);
    await page.getByLabel("Nội dung").fill(TEXT);
    await page.getByRole("button", { name: "Lưu nguồn" }).click();
    await expect(page.getByRole("link", { name: st.title })).toBeVisible({ timeout: 30_000 });
    await noHScroll(page);
  });
  await S(page, vp, "S02-new-lesson", async () => {
    await page.goto("/lessons/new");
    await page.getByLabel("Tên bài").fill(st.title);
    await page.locator("label.check").filter({ hasText: st.title }).locator("input").check();
    await page.getByRole("button", { name: "Tạo bài" }).click();
    await expect(page).toHaveURL(/\/lessons\/[^/?]+\?tab=editor/, { timeout: 30_000 });
    st.lessonUrl = new URL(page.url()).pathname;
  });
  await S(page, vp, "S02-generate", async () => {
    await page.getByRole("button", { name: "Sinh bản nháp" }).click();
    await expect(page.getByText(/Đã sinh \d+ khối/)).toBeVisible({ timeout: 90_000 });
    await noHScroll(page);
  });
  await S(page, vp, "S03-edit-and-provenance", async () => {
    await page.locator(".tree-node").filter({ hasText: /đoạn nguồn/ }).first().click();
    await expect(page.locator(".evidence blockquote").first()).toBeVisible();
    st.blockId = new URL(page.url()).searchParams.get("block") ?? "";
    await page.getByRole("button", { name: "Sửa nội dung" }).click();
    const ta = page.locator("textarea").first();
    await ta.fill((await ta.inputValue()) + " (đã chỉnh)");
    await page.getByRole("button", { name: "Lưu", exact: true }).click();
    await expect(page.getByRole("button", { name: "Sửa nội dung" })).toBeVisible({ timeout: 30_000 });
  });
  await S(page, vp, "S04-review-all", async () => {
    await approveAll(page);
  });
  await S(page, vp, "S05-publish-assign", async () => {
    await publishAssign(page, vp);
  });
  await S(page, vp, "S06-history", async () => {
    await page.getByRole("tab", { name: "Lịch sử" }).click();
    await page.getByRole("button", { name: /^Xem bản #/ }).first().click();
    await expect(page.locator(".tree.snapshot .block-card").first()).toBeVisible();
  });
  rec({ vp, check: "teacher-console-errors", n: errs.length, sample: errs.slice(0, 3) });
  rec({ vp, check: "requests", ...cnt });
  rec({ vp, check: "csrf-missing", n: badCsrf.length, sample: badCsrf.slice(0, 3) });
});

test("T2 student: answer 2 questions, explanation after submit, provenance blocked", async ({ page }, info) => {
  const vp = info.project.name;
  const errs: string[] = [];
  watch(page, errs);
  await S(page, vp, "S07-student-home", async () => {
    await login(page, STUDENT[vp]!);
    await expect(page.getByRole("heading", { name: "Bài được giao" })).toBeVisible();
    await noHScroll(page);
    rec({ vp, check: "load-student-ms", ms: await loadMs(page) });
  });
  await S(page, vp, "S07-answer-2", async () => {
    await page.locator(".assignment-card").filter({ hasText: st.title }).first().click();
    await expect(page).toHaveURL(/\/student\/assignments\//);
    st.assignmentUrl = new URL(page.url()).pathname;
    for (let i = 0; i < 2; i++) {
      const item = page.locator("section.item").nth(i);
      await expect(item.locator(".explanation")).toHaveCount(0);
      await item.getByRole("button", { name: "Nộp câu trả lời" }).waitFor({ timeout: 30_000 });
      // Items can be MCQ, NUMERIC or free text.
      if (await item.locator(".option").count()) await item.locator(".option").first().click();
      else if (await item.getByLabel("Đáp số").count()) await item.getByLabel("Đáp số").fill("10");
      else await item.getByLabel("Câu trả lời").fill("Trả lời thử cho kiểm thử phát hành.");
      await item.getByRole("button", { name: "Nộp câu trả lời" }).click();
      await expect(item.getByRole("status")).toContainText(/Đúng|Chưa đúng/, { timeout: 30_000 });
      await expect(item.locator(".explanation")).not.toBeEmpty();
    }
    await noHScroll(page);
  });
  await S(page, vp, "S07-provenance-blocked", async () => {
    const r = await page.request.get(`/v1/blocks/${st.blockId}/provenance`);
    rec({ vp, check: "student-provenance-status", status: r.status() });
    expect(r.status()).toBe(404); // PR-08
  });
  rec({ vp, check: "student-console-errors", n: errs.length, sample: errs.slice(0, 3) });
});

test("T3 teacher: withdraw (and republish on 1280)", async ({ page }, info) => {
  const vp = info.project.name;
  await login(page, "gv.dia@preclass.local");
  await S(page, vp, "withdraw", async () => {
    await page.goto(`${st.lessonUrl}?tab=publish`);
    await page.getByRole("button", { name: "Thu hồi…" }).click();
    await page.getByLabel("Lý do thu hồi").fill("Kiểm thử phát hành 19/11");
    await page.getByRole("button", { name: "Xác nhận thu hồi" }).click();
    await expect(page.getByText(/Đã thu hồi bản xuất bản/)).toBeVisible({ timeout: 30_000 });
  });
  if (vp === "1280") {
    await S(page, vp, "republish-new-revision", async () => {
      await page.getByRole("tab", { name: "Lịch sử" }).click();
      const newRev = page.getByRole("button", { name: "Tạo bản sửa mới" });
      if (await newRev.count()) await newRev.click();
      await approveAll(page);
      await publishAssign(page, vp);
    });
  }
});

test("T4 student: sees withdrawn notice", async ({ page }, info) => {
  const vp = info.project.name;
  await login(page, STUDENT[vp]!);
  await S(page, vp, "withdrawn-notice", async () => {
    await page.goto(st.assignmentUrl);
    await expect(page.getByText(/thu hồi/).first()).toBeVisible({ timeout: 30_000 });
  });
});
