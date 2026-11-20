import { useEffect, useState } from "react";

/** No request may hang forever (Render Free restarts take up to a minute): every call is aborted after this. */
export const REQUEST_TIMEOUT_MS = 60_000;

/** An AbortSignal that aborts after `ms`, or earlier when `outer` aborts. */
export function withTimeout(ms: number, outer?: AbortSignal | null): AbortSignal {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  const stop = () => {
    clearTimeout(timer);
    ctrl.abort();
  };
  if (outer?.aborted) stop();
  else outer?.addEventListener("abort", stop, { once: true });
  ctrl.signal.addEventListener("abort", () => clearTimeout(timer), { once: true });
  return ctrl.signal;
}

/** fetch with the default timeout. Works with openapi-fetch (which passes a Request) and with plain (url, init). */
export const timeoutFetch: typeof fetch = (input, init) => {
  const outer = init?.signal ?? (input instanceof Request ? input.signal : undefined);
  const signal = withTimeout(REQUEST_TIMEOUT_MS, outer);
  return input instanceof Request ? fetch(new Request(input, { signal })) : fetch(input, { ...init, signal });
};

/** True once `flag` has been continuously true for `ms`; false again as soon as it turns false. */
export function useAfter(flag: boolean, ms: number): boolean {
  const [late, setLate] = useState(false);
  useEffect(() => {
    if (!flag) {
      setLate(false);
      return;
    }
    const t = setTimeout(() => setLate(true), ms);
    return () => clearTimeout(t);
  }, [flag, ms]);
  return late;
}
