import { expect, test } from "@playwright/test";

/** Read-only (GET only, safe on cloud): every stylesheet a page links must answer 200 + text/css. A 404 text/plain here is deployment skew (HTML from one deploy, assets from another). */
for (const route of ["/", "/login"]) {
  test(`${route}: every /_next/static css is 200 text/css`, async ({ request }) => {
    const html = await (await request.get(route)).text();
    const hrefs = [...new Set(html.match(/\/_next\/static\/[^"']+?\.css/g) ?? [])];
    expect(hrefs.length, "page links at least one stylesheet").toBeGreaterThan(0);
    for (const href of hrefs) {
      const res = await request.get(href);
      expect(res.status(), href).toBe(200);
      expect(res.headers()["content-type"], href).toMatch(/^text\/css/);
    }
  });
}
