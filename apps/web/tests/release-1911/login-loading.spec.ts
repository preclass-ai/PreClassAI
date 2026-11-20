import { mkdirSync } from "node:fs";
import { expect, test, type Page } from "@playwright/test";

/** /login must never hang on "Đang tải…": the requests are simulated by blocking routes (no real API needed). */
const OUT = "test-results/login-loading";
const UNAUTH = { type: "about:blank", title: "t", status: 401, detail: "", code: "UNAUTHENTICATED" };
const json = (status: number, body: unknown) => ({ status, contentType: "application/json", body: JSON.stringify(body) });

async function mockMe401(page: Page) {
  await page.route("**/v1/me", (r) => r.fulfill(json(401, UNAUTH)));
}

const accountForm = (page: Page) => page.getByLabel("Email hoặc mã học sinh");
const shot = async (page: Page, name: string, vp: string) => {
  mkdirSync(OUT, { recursive: true });
  await page.screenshot({ path: `${OUT}/${name}-${vp}.png`, fullPage: true });
};

test("me 401 + config ok: the guest button and the sign-in entry show right away", async ({ page }, info) => {
  await mockMe401(page);
  await page.route("**/v1/auth/config", (r) => r.fulfill(json(200, { guestEnabled: true })));
  await page.goto("/login");
  await expect(page.getByRole("button", { name: "Vào làm thử (không cần tài khoản)" })).toBeVisible({ timeout: 5_000 });
  await expect(page.getByText("Giáo viên / có tài khoản")).toBeVisible();
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
  await shot(page, "config-ok", info.project.name);
});

test("config answers only after 30 s: form within ~3 s, 'server is starting' + retry by ~16 s, no endless spinner", async ({ page }, info) => {
  await mockMe401(page);
  await page.route("**/v1/auth/config", async (route) => {
    await new Promise((r) => setTimeout(r, 30_000));
    await route.fulfill(json(200, { guestEnabled: true })).catch(() => undefined); // already aborted by the 15 s timeout
  });
  await page.goto("/login");
  await expect(accountForm(page)).toBeVisible({ timeout: 8_000 }); // the grace period is 3 s
  await shot(page, "slow-config-3s", info.project.name);
  await expect(page.getByText(/Máy chủ đang khởi động/)).toBeVisible({ timeout: 20_000 });
  await expect(page.getByRole("button", { name: "Thử lại" })).toBeVisible();
  await expect(page.getByText("Đang tải…")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Vào làm thử (không cần tài khoản)" })).toHaveCount(0);
  await shot(page, "slow-config-timeout", info.project.name);
});

test("config 500: sign-in form stays, retry brings the guest button back", async ({ page }, info) => {
  await mockMe401(page);
  let healthy = false;
  await page.route("**/v1/auth/config", (r) =>
    r.fulfill(healthy ? json(200, { guestEnabled: true }) : json(500, { ...UNAUTH, status: 500, code: "INTERNAL" })),
  );
  await page.goto("/login");
  await expect(page.getByText(/Máy chủ đang khởi động/)).toBeVisible({ timeout: 8_000 });
  await expect(accountForm(page)).toBeVisible();
  await shot(page, "config-500", info.project.name);
  healthy = true;
  await page.getByRole("button", { name: "Thử lại" }).click();
  await expect(page.getByRole("button", { name: "Vào làm thử (không cần tài khoản)" })).toBeVisible({ timeout: 8_000 });
});

test("a browser extension that throws and breaks fetch does not stop the page", async ({ page }, info) => {
  await mockMe401(page);
  await page.addInitScript(() => {
    setTimeout(() => {
      throw new Error("extension: injected script failed");
    }, 50);
    const real = window.fetch.bind(window);
    window.fetch = (input, init) => {
      const url = typeof input === "string" ? input : input instanceof Request ? input.url : String(input);
      if (url.includes("/v1/auth/config")) throw new TypeError("extension patched fetch badly");
      return real(input, init);
    };
  });
  await page.goto("/login");
  await expect(accountForm(page)).toBeVisible({ timeout: 8_000 });
  await expect(page.getByText(/Máy chủ đang khởi động/)).toBeVisible();
  await shot(page, "extension", info.project.name);
});
