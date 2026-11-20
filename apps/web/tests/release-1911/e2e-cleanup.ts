import { request, type FullConfig } from "@playwright/test";

/**
 * After every release E2E run: withdraw every published "[E2E]" lesson so no test lesson stays assigned to anyone.
 * Needs E2E_TEACHER_PASSWORD (gv.dia). Without it nothing is touched and a reminder is printed.
 */
export default async function globalTeardown(config: FullConfig) {
  const baseURL = config.projects[0]?.use.baseURL;
  const password = process.env.E2E_TEACHER_PASSWORD ?? process.env.SEED_TEACHER_PASSWORD ?? process.env.SEED_PASSWORD;
  if (!baseURL || !password) {
    console.log("[e2e-cleanup] skipped: set E2E_TEACHER_PASSWORD to withdraw the [E2E] lessons after the run.");
    return;
  }
  const api = await request.newContext({ baseURL, extraHTTPHeaders: { "X-PreClass-CSRF": "1" } });
  try {
    const login = await api.post("/v1/auth/login", { data: { identifier: "gv.dia@preclass.local", password } });
    if (!login.ok()) {
      console.log(`[e2e-cleanup] teacher login failed (${login.status()}): [E2E] lessons were NOT withdrawn.`);
      return;
    }
    const lessons = ((await (await api.get("/v1/lessons")).json()).items ?? []) as {
      id: string;
      title: string;
      publishedVersionId: string | null;
    }[];
    let withdrawn = 0;
    for (const l of lessons.filter((x) => x.title.startsWith("[E2E]") && x.publishedVersionId)) {
      const r = await api.post(`/v1/published/${l.publishedVersionId}/withdraw`, { data: { reason: "Dọn dẹp sau khi chạy E2E" } });
      if (r.ok()) withdrawn++;
      else if (r.status() !== 409) console.log(`[e2e-cleanup] could not withdraw "${l.title}" (${r.status()})`);
    }
    console.log(`[e2e-cleanup] withdrew ${withdrawn} [E2E] lesson(s)`);
    await api.post("/v1/auth/logout");
  } finally {
    await api.dispose();
  }
}
