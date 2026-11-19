import { QueryClient, QueryObserver } from "@tanstack/react-query";
import { expect, it } from "vitest";
import { refresh } from "@/lib/query";

/** The page is subscribed; its first GET started before the mutation and answers with the old rows. */
async function scenario(update: (qc: QueryClient) => Promise<unknown>) {
  const qc = new QueryClient();
  let rows = ["a"];
  const queryFn = () => new Promise<string[]>((res) => { const snap = [...rows]; setTimeout(() => res(snap), 40); });
  const unsub = new QueryObserver(qc, { queryKey: ["sources"], queryFn }).subscribe(() => undefined);
  await new Promise((r) => setTimeout(r, 5)); // first fetch is now in flight
  rows = ["a", "new"]; // POST committed
  await update(qc);
  await new Promise((r) => setTimeout(r, 120));
  unsub();
  return qc.getQueryData(["sources"]);
}

it("plain invalidate misses the new row while the first fetch is in flight (the bug)", async () => {
  expect(await scenario((qc) => qc.invalidateQueries({ queryKey: ["sources"] }))).toEqual(["a"]);
});

it("refresh() shows the new row", async () => {
  expect(await scenario((qc) => refresh(qc, { queryKey: ["sources"] }))).toEqual(["a", "new"]);
});
