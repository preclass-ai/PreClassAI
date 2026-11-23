"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { Button, Notice } from "@/components/ui";
import { api, unwrap } from "@/lib/api";

// Options the STUDENT chooses (ADR-0013). Plain wording: nothing here labels the student.
const KEY = ["preferences"];
const TOGGLES: [string, string][] = [
  ["chia_nho_tung_buoc", "Chia nhỏ từng bước"],
  ["uu_tien_bang_so_lieu", "Ưu tiên bảng số liệu"],
  ["uu_tien_giai_thich", "Ưu tiên phần giải thích"],
  ["nhac_tien_do", "Nhắc tiến độ"],
];

export function usePersonalizationOn(): boolean {
  const cfg = useQuery({
    queryKey: ["auth-config"],
    queryFn: () => unwrap(api.GET("/v1/auth/config")),
    staleTime: Infinity,
    retry: false,
  });
  return cfg.data?.personalizationEnabled === true;
}

export function usePrefs(enabled: boolean): Record<string, string> {
  const q = useQuery({ queryKey: KEY, enabled, retry: false, queryFn: () => unwrap(api.GET("/v1/student/preferences")) });
  return q.data?.preferences ?? {};
}

export function PersonalizationBar({ focus, onFocus }: { focus: boolean; onFocus: (on: boolean) => void }) {
  const on = usePersonalizationOn();
  const prefs = usePrefs(on);
  const qc = useQueryClient();
  const inflight = useRef(0);
  const [mine, setMine] = useState<Record<string, string> | null>(null);
  const view = mine ?? prefs;
  if (!on) return null;

  async function save(preferences: Record<string, "on" | "off" | "5" | "10">) {
    // Optimistic and synchronous (local state, not the query cache): a controlled checkbox must follow the click at once.
    const next = { ...view };
    for (const [k, v] of Object.entries(preferences)) {
      if (v === "off") delete next[k];
      else next[k] = v;
    }
    setMine(next);
    inflight.current += 1;
    try {
      const res = await unwrap(api.PUT("/v1/student/preferences", { body: { preferences } }));
      // Answers can arrive out of order: only the last one may overwrite what the student already sees.
      if (inflight.current === 1) {
        qc.setQueryData(KEY, res);
        setMine(null);
      }
    } catch {
      if (inflight.current === 1) setMine(null); // refused or offline: back to what the server has
    } finally {
      inflight.current -= 1;
    }
  }
  async function reset() {
    try {
      qc.setQueryData(KEY, await unwrap(api.DELETE("/v1/student/preferences")));
      setMine(null);
    } catch {
      /* keep the current state */
    }
  }
  function toggleFocus() {
    const next = !focus;
    onFocus(next);
    if (next && !view.focus_mode_used) void save({ focus_mode_used: "on" }); // only so the survey can count "used at least once"
  }

  return (
    <section className="pers-bar" aria-label="Cách học hôm nay" data-tour="pers">
      <details>
        <summary>Em muốn học theo cách nào hôm nay?</summary>
        <fieldset className="pers-options">
          <legend className="muted small">Các lựa chọn chỉ của riêng em, đổi bất cứ lúc nào.</legend>
          {TOGGLES.map(([key, label]) => (
            <label key={key} className="pers-option">
              <input type="checkbox" checked={view[key] === "on"} onChange={(e) => void save({ [key]: e.target.checked ? "on" : "off" })} />
              {label}
            </label>
          ))}
          <label className="pers-option">
            Hẹn giờ tập trung
            <select value={view.hen_gio_tap_trung ?? "off"} onChange={(e) => void save({ hen_gio_tap_trung: e.target.value as "off" | "5" | "10" })}>
              <option value="off">Tắt</option>
              <option value="5">5 phút</option>
              <option value="10">10 phút</option>
            </select>
          </label>
          <Button variant="secondary" onClick={() => void reset()}>
            Tắt hết
          </Button>
        </fieldset>
      </details>
      <Button variant={focus ? "primary" : "secondary"} aria-pressed={focus} onClick={toggleFocus} className="pers-focus">
        {focus ? "Thoát chế độ tập trung" : "Chế độ tập trung"}
      </Button>
    </section>
  );
}

const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

/** Countdown for the focus timer; when it ends, a short, friendly break reminder (no sound, no motion). */
export function FocusTimer({ minutes }: { minutes: number }) {
  const [left, setLeft] = useState(minutes * 60);
  const [rest, setRest] = useState(false);
  useEffect(() => {
    if (rest) return;
    const t = setInterval(() => {
      setLeft((l) => {
        if (l <= 1) {
          setRest(true);
          return 0;
        }
        return l - 1;
      });
    }, 1000);
    return () => clearInterval(t);
  }, [rest]);
  if (rest) {
    return (
      <Notice tone="info">
        Em đã học {minutes} phút. Nghỉ mắt một chút rồi quay lại nhé.{" "}
        <Button
          variant="secondary"
          onClick={() => {
            setLeft(minutes * 60);
            setRest(false);
          }}
        >
          Học tiếp
        </Button>
      </Notice>
    );
  }
  return (
    <p className="focus-timer" role="timer" aria-label="Thời gian tập trung còn lại">
      ⏱ {mmss(left)}
    </p>
  );
}
