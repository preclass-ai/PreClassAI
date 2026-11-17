"use client";

import { useCallback, useEffect, useRef, useState } from "react";

const PREFIX = "preclass:draft:";

function read<T>(key: string): T | null {
  try {
    const raw = window.sessionStorage.getItem(PREFIX + key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function write(key: string, value: unknown) {
  try {
    window.sessionStorage.setItem(PREFIX + key, JSON.stringify(value));
  } catch {
    /* storage full or blocked: the in-memory value still works */
  }
}

function remove(key: string) {
  try {
    window.sessionStorage.removeItem(PREFIX + key);
  } catch {
    /* ignore */
  }
}

/**
 * Local autosave for an unsaved edit (handoff §10: "không làm mất nội dung đã nhập").
 * The key must include the server version the edit started from, so a draft never resurfaces
 * on top of content that changed since; the server still rejects stale saves with VERSION_CONFLICT.
 * Session storage only: drafts stay in this tab and never leave the browser.
 */
export function useDraft<T>(key: string, initial: T) {
  const [saved] = useState(() => (typeof window === "undefined" ? null : read<T>(key)));
  const [value, setValue] = useState<T>(saved ?? initial);
  const [restored, setRestored] = useState(saved !== null);
  const dirty = useRef(saved !== null);

  useEffect(() => {
    if (dirty.current) write(key, value);
  }, [key, value]);

  const update = useCallback((next: T) => {
    dirty.current = true;
    setValue(next);
  }, []);

  const discard = useCallback(
    (reset: T) => {
      dirty.current = false;
      remove(key);
      setRestored(false);
      setValue(reset);
    },
    [key],
  );

  return { value, setValue: update, discard, restored };
}
