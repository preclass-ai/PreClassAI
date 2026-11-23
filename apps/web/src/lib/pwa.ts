"use client";

import { useSyncExternalStore } from "react";

/** Chrome/Edge/Samsung only; Safari never fires it (iPhone users add the app from the Share sheet). */
export interface InstallPromptEvent extends Event {
  prompt(): Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed" }>;
}

type PwaWindow = Window & { __pcInstall?: InstallPromptEvent | null; __pcInstalled?: boolean };
const EVENT = "pc-install";

export interface Device {
  ios: boolean;
  ipad: boolean;
  android: boolean;
  mobile: boolean;
  /** Zalo, Facebook, Messenger…: their built-in browser cannot install a web app. */
  inApp: string | null;
  /** Chrome/Edge/Firefox on iPhone: same Share sheet, button in the address bar. */
  iosOther: boolean;
  /** Safari major version (iOS 26 hides Share behind the ⋯ button). */
  safari: number;
  samsung: boolean;
  macSafari: boolean;
}

/** Pure: easy to test with any user agent. */
export function detectDevice(ua: string, platform = "", touchPoints = 0): Device {
  const ipadOs = platform === "MacIntel" && touchPoints > 1; // iPadOS reports itself as a Mac
  const ipad = /iPad/.test(ua) || ipadOs;
  const ios = /iPhone|iPod/.test(ua) || ipad;
  const android = /Android/i.test(ua);
  const inAppMatch = ua.match(/Zalo|FBAN|FBAV|FB_IAB|Messenger|Instagram|Line\/|TikTok|musical_ly|MicroMessenger/i);
  const inApp = inAppMatch ? (/zalo/i.test(inAppMatch[0]) ? "Zalo" : /tiktok|musical/i.test(inAppMatch[0]) ? "TikTok" : /instagram/i.test(inAppMatch[0]) ? "Instagram" : "Facebook") : null;
  return {
    ios,
    ipad,
    android,
    mobile: ios || android,
    inApp,
    iosOther: ios && /CriOS|FxiOS|EdgiOS|OPiOS|GSA\//.test(ua),
    safari: Number((ua.match(/Version\/(\d+)/) ?? [])[1] ?? 0),
    samsung: /SamsungBrowser/i.test(ua),
    macSafari: !ios && /Macintosh/.test(ua) && /Safari\//.test(ua) && !/Chrome|Chromium|Edg\//.test(ua),
  };
}

let device: Device | null = null;
function getDevice(): Device {
  device ??= detectDevice(navigator.userAgent || "", navigator.platform || "", navigator.maxTouchPoints || 0);
  return device;
}

export function isStandalone(): boolean {
  try {
    return (
      window.matchMedia?.("(display-mode: standalone)").matches ||
      window.matchMedia?.("(display-mode: minimal-ui)").matches ||
      (navigator as Navigator & { standalone?: boolean }).standalone === true
    );
  } catch {
    return false;
  }
}

function subscribe(cb: () => void) {
  window.addEventListener(EVENT, cb);
  const mq = window.matchMedia?.("(display-mode: standalone)");
  mq?.addEventListener?.("change", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    mq?.removeEventListener?.("change", cb);
  };
}

/** null on the server and during hydration, then the real device. */
export function useDevice(): Device | null {
  return useSyncExternalStore(subscribe, getDevice, () => null);
}

export function useStandalone(): boolean {
  return useSyncExternalStore(subscribe, isStandalone, () => false);
}

/** The deferred one-tap install event, when the browser offers one. */
export function useInstallPrompt(): InstallPromptEvent | null {
  return useSyncExternalStore(subscribe, () => (window as PwaWindow).__pcInstall ?? null, () => null);
}

export function useJustInstalled(): boolean {
  return useSyncExternalStore(subscribe, () => !!(window as PwaWindow).__pcInstalled, () => false);
}

/** Shows the system install dialog once (the event cannot be reused). */
export async function promptInstall(): Promise<"accepted" | "dismissed" | "unavailable"> {
  const w = window as PwaWindow;
  const ev = w.__pcInstall;
  if (!ev) return "unavailable";
  w.__pcInstall = null;
  window.dispatchEvent(new Event(EVENT));
  try {
    await ev.prompt();
    return (await ev.userChoice).outcome;
  } catch {
    return "dismissed";
  }
}
