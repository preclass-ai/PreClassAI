/**
 * `?next=` after login: only a same-origin path. Rejects absolute and protocol-relative URLs and backslash
 * tricks such as `/\evil.com`, which browsers resolve to another host.
 */
export function safeNext(next: string | null, origin = "http://localhost"): string | null {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) return null;
  try {
    const url = new URL(next, origin);
    if (url.origin !== new URL(origin).origin || url.pathname === "/login") return null;
    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return null;
  }
}
