"use client";

import { useCallback, useEffect, useSyncExternalStore } from "react";

export type ThemeChoice = "light" | "dark" | "system";
export const THEME_KEY = "preclass.theme";
const EVENT = "preclass-theme";

/**
 * Runs in <head> before the first paint, so a dark-mode user never sees a white flash.
 * Kept as a string: it must not depend on the bundle. CSP allows inline scripts (next.config.ts).
 */
export const THEME_BOOT_SCRIPT = `(function(){try{var c=localStorage.getItem("${THEME_KEY}");var d=c==="dark"||(c!=="light"&&window.matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=d?"dark":"light";}catch(e){document.documentElement.dataset.theme="light";}})();`;

function readChoice(): ThemeChoice {
  try {
    const v = localStorage.getItem(THEME_KEY);
    return v === "light" || v === "dark" ? v : "system";
  } catch {
    return "system"; // storage blocked: follow the device
  }
}

function systemDark(): boolean {
  return typeof window !== "undefined" && !!window.matchMedia?.("(prefers-color-scheme: dark)").matches;
}

export function resolveTheme(choice: ThemeChoice): "light" | "dark" {
  return choice === "system" ? (systemDark() ? "dark" : "light") : choice;
}

function apply(choice: ThemeChoice) {
  document.documentElement.dataset.theme = resolveTheme(choice);
}

export function setTheme(choice: ThemeChoice) {
  try {
    if (choice === "system") localStorage.removeItem(THEME_KEY);
    else localStorage.setItem(THEME_KEY, choice);
  } catch {
    /* storage blocked: the choice lasts until reload */
  }
  apply(choice);
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(cb: () => void) {
  const mq = window.matchMedia?.("(prefers-color-scheme: dark)");
  const onSystem = () => {
    if (readChoice() === "system") apply("system");
    cb();
  };
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", onSystem); // another tab changed it
  mq?.addEventListener?.("change", onSystem);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", onSystem);
    mq?.removeEventListener?.("change", onSystem);
  };
}

/** Current resolved theme ("light" | "dark"), kept in sync with the toggle, other tabs and the OS setting. */
export function useTheme(): { theme: "light" | "dark"; choice: ThemeChoice; toggle: () => void; set: (c: ThemeChoice) => void } {
  const theme = useSyncExternalStore(
    subscribe,
    () => (document.documentElement.dataset.theme === "dark" ? "dark" : "light"),
    () => "light" as const,
  );
  const choice = useSyncExternalStore(subscribe, readChoice, () => "system" as const);
  useEffect(() => {
    // The boot script normally did this already; this covers tests and pages rendered without it.
    if (!document.documentElement.dataset.theme) apply(readChoice());
  }, []);
  const toggle = useCallback(() => setTheme(theme === "dark" ? "light" : "dark"), [theme]);
  return { theme, choice, toggle, set: setTheme };
}

/** Sun/moon switch for the top bar. */
export function ThemeToggle() {
  const { theme, toggle } = useTheme();
  const dark = theme === "dark";
  return (
    <button
      type="button"
      className="theme-toggle"
      role="switch"
      aria-checked={dark}
      aria-label="Chế độ tối"
      title={dark ? "Đang dùng giao diện tối · bấm để chuyển sang sáng" : "Đang dùng giao diện sáng · bấm để chuyển sang tối"}
      onClick={toggle}
      data-tour="theme"
    >
      <span className="theme-track" aria-hidden="true">
        <span className="theme-knob">
          {dark ? (
            <svg viewBox="0 0 24 24" width="14" height="14"><path d="M20 14.5A8 8 0 0 1 9.5 4a8 8 0 1 0 10.5 10.5z" fill="currentColor" /></svg>
          ) : (
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round">
              <circle cx="12" cy="12" r="4.2" fill="currentColor" stroke="none" />
              <path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6" />
            </svg>
          )}
        </span>
      </span>
      <span className="theme-label">{dark ? "Tối" : "Sáng"}</span>
    </button>
  );
}
