import type { QueryClient, QueryFilters } from "@tanstack/react-query";

/**
 * Refresh queries after a mutation, even if their FIRST fetch is still in flight.
 * `invalidateQueries` alone joins an in-flight fetch of a query that has no data yet, and that fetch started before the
 * mutation: the list then misses the new row (seen on the cloud demo, where the first GET is slow).
 */
export async function refresh(qc: QueryClient, filters: QueryFilters): Promise<void> {
  await qc.cancelQueries(filters);
  await qc.invalidateQueries(filters);
}
