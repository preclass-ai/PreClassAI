"use client";

import { useQuery } from "@tanstack/react-query";
import { useCallback, useMemo, useSyncExternalStore } from "react";
import { api, unwrap } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { isSpeciesId, progressOf, SPECIES_BY_ID, type AssignmentLike, type Progress, type Species, type SpeciesId } from "./species";

/**
 * The garden choice lives in this browser only (localStorage, per user id): no student data leaves the device and the
 * API needs no change. Progress comes from the assignment list on the server, so a new device only asks for the seed again.
 */
interface Saved {
  species: SpeciesId | null;
  plantedAt: string | null;
  tours: string[]; // guided tours already shown ("home", "assignment")
}
const EMPTY: Saved = { species: null, plantedAt: null, tours: [] };
const EVENT = "preclass-garden";
const keyFor = (uid: string | undefined) => `preclass.garden.${uid ?? "anon"}`;

function readRaw(key: string): string | null {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function parse(raw: string | null): Saved {
  if (!raw) return EMPTY;
  try {
    const v = JSON.parse(raw) as Partial<Saved>;
    return {
      species: isSpeciesId(v.species) ? v.species : null,
      plantedAt: typeof v.plantedAt === "string" ? v.plantedAt : null,
      tours: Array.isArray(v.tours) ? v.tours.filter((t): t is string => typeof t === "string") : [],
    };
  } catch {
    return EMPTY;
  }
}

function subscribe(cb: () => void) {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}

export function useGarden() {
  const { user } = useAuth();
  const key = keyFor(user?.id);
  const raw = useSyncExternalStore(subscribe, () => readRaw(key), () => null);
  // Hydration: the server snapshot is null; `ready` turns true on the client so the picker never flashes during SSR.
  const ready = useSyncExternalStore(subscribe, () => true, () => false);
  const saved = useMemo(() => parse(raw), [raw]);

  const write = useCallback(
    (patch: Partial<Saved>) => {
      const next = { ...parse(readRaw(key)), ...patch };
      try {
        localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* storage blocked: the choice lasts for this page only */
      }
      window.dispatchEvent(new Event(EVENT));
    },
    [key],
  );

  const choose = useCallback((id: SpeciesId) => write({ species: id, plantedAt: new Date().toISOString() }), [write]);
  const markTour = useCallback(
    (name: string) => {
      const seen = parse(readRaw(key)).tours;
      if (!seen.includes(name)) write({ tours: [...seen, name] });
    },
    [key, write],
  );
  const species: Species | null = saved.species ? SPECIES_BY_ID[saved.species] : null;
  return { ready, species, tours: saved.tours, choose, markTour };
}

/** The mascot is simply the chosen species (null until the student plants a seed). */
export function useMascot(): Species | null {
  return useGarden().species;
}

/**
 * Garden progress from the student's own assignment list (same query as the home page, so no extra request there).
 * The server marks an assignment DONE once every question is answered, which can only happen before its due date.
 * null until the list has loaded.
 */
export function useAssignmentList() {
  return useQuery({ queryKey: ["student-assignments"], queryFn: () => unwrap(api.GET("/v1/student/assignments")) }).data?.items;
}

export function useProgress(): Progress | null {
  const items = useAssignmentList();
  return useMemo(() => (items ? progressOf(items) : null), [items]);
}

/** The streak if this assignment were finished now (it may not raise it, e.g. when a later one was missed). */
export function streakIfDone(items: readonly AssignmentLike[], assignmentId: string): number {
  return progressOf(items.map((a) => (a.id === assignmentId ? { ...a, status: "DONE" as const } : a))).streak;
}

/** Ask the mascot to start the guided tour from anywhere (mascot dock, garden card, FAQ answer). */
export const TOUR_EVENT = "preclass-tour-start";
export function startTour() {
  window.dispatchEvent(new Event(TOUR_EVENT));
}
export const PICKER_EVENT = "preclass-seed-picker";
export function openSeedPicker() {
  window.dispatchEvent(new Event(PICKER_EVENT));
}
