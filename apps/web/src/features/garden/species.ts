/**
 * The six seeds a student can plant. The seed picked first is also the student's mascot: it guides them through the app
 * and speaks for HABIT AI inside each question. Sprites: public/garden/<id>/<stage>.webp, stages 0..6.
 */
export type SpeciesId = "knowledge" | "sakura" | "apple" | "ginkgo" | "wisteria" | "lotus";

export interface Species {
  id: SpeciesId;
  name: string; // the plant
  mascot: string; // what the mascot calls itself
  trait: string; // one line under the card
  accent: string; // CSS color for rings and bubbles (readable on light and dark surfaces)
  stages: readonly [string, string, string, string, string, string, string];
  hello: string; // first words after planting
  cheer: string; // when the student keeps the streak today
  nudge: string; // when today's goal is not met yet
}

export const SPECIES: readonly Species[] = [
  {
    id: "knowledge",
    name: "Cây tri thức",
    mascot: "Bé Tri",
    trait: "Cân bằng, bền bỉ",
    accent: "#4f9a3a",
    stages: ["Hạt giống", "Nảy mầm", "Mầm non", "Cây con", "Tán xanh", "Ra hoa", "Cây tri thức"],
    hello: "Chào em, mình là Bé Tri! Mỗi bài em làm xong, mình lại lớn thêm một chút.",
    cheer: "Em làm xong hết bài rồi, mình được tưới no nê, cảm ơn nha!",
    nudge: "Làm xong bài đang chờ là mình lớn thêm một chút đó.",
  },
  {
    id: "sakura",
    name: "Hoa anh đào",
    mascot: "Bé Đào",
    trait: "Tinh thần tích cực",
    accent: "#e0679a",
    stages: ["Hạt giống", "Nảy mầm", "Mầm non", "Đơm nụ", "Nở hoa", "Rực rỡ", "Mùa anh đào"],
    hello: "Hi em, Bé Đào đây! Mình cùng làm bài thật vui để mình nở thật nhiều hoa nhé.",
    cheer: "Yay, xong hết bài rồi, mình có thêm nụ hoa nhờ em!",
    nudge: "Xong thêm một bài là mình nở thêm hoa đó, cố lên!",
  },
  {
    id: "apple",
    name: "Cây táo",
    mascot: "Bé Táo",
    trait: "Kiên trì, kết quả ngọt",
    accent: "#d9473b",
    stages: ["Hạt giống", "Nảy mầm", "Mầm non", "Cây con", "Ra hoa", "Kết trái", "Mùa táo chín"],
    hello: "Chào em, Bé Táo đây! Làm đều từng bài thì trái ngọt sẽ tới thôi.",
    cheer: "Chăm quá, hết bài rồi, trái của mình ngọt thêm!",
    nudge: "Kiên trì thêm chút nữa, làm xong bài đang chờ nhé.",
  },
  {
    id: "ginkgo",
    name: "Cây ngân hạnh",
    mascot: "Bé Ngân",
    trait: "Trưởng thành, vững vàng",
    accent: "#d29a0a",
    stages: ["Hạt giống", "Nảy mầm", "Mầm non", "Cây con", "Thay lá", "Lá vàng", "Ngân hạnh cổ thụ"],
    hello: "Chào em, mình là Bé Ngân. Từ từ mà chắc, mình sẽ cùng em vững vàng qua từng bài.",
    cheer: "Không bỏ bài nào, lá của mình vàng hơn rồi đó.",
    nudge: "Mình vẫn đang chờ em làm bài nè.",
  },
  {
    id: "wisteria",
    name: "Hoa tử đằng",
    mascot: "Bé Tím",
    trait: "Nhẹ nhàng, bền bỉ",
    accent: "#8b62d6",
    stages: ["Hạt giống", "Nảy mầm", "Mầm non", "Leo giàn", "Chớm hoa", "Buông chùm", "Thác tử đằng"],
    hello: "Chào em, Bé Tím đây. Mình leo chậm nhưng không bao giờ bỏ cuộc, em cũng vậy nha.",
    cheer: "Thêm một chùm hoa tím rồi, cảm ơn em nhé.",
    nudge: "Nhẹ nhàng làm từng câu thôi, xong bài là mình leo thêm một đoạn.",
  },
  {
    id: "lotus",
    name: "Sen tri tuệ",
    mascot: "Bé Sen",
    trait: "Tập trung, bình an",
    accent: "#d9658a",
    stages: ["Hạt sen", "Nảy mầm", "Lá non", "Đơm nụ", "Nụ lớn", "Hé nở", "Sen tri tuệ"],
    hello: "Chào em, mình là Bé Sen. Hít một hơi, tập trung, mình cùng học nhé.",
    cheer: "Bài nào cũng trọn vẹn. Mình hé nở thêm chút rồi.",
    nudge: "Bình tĩnh làm từng câu, xong bài là trọn vẹn.",
  },
] as const;

export const SPECIES_BY_ID = Object.fromEntries(SPECIES.map((s) => [s.id, s])) as Record<SpeciesId, Species>;

export function isSpeciesId(v: unknown): v is SpeciesId {
  return typeof v === "string" && v in SPECIES_BY_ID;
}

/**
 * The tree grows with the number of assignments the student has finished (all questions answered before the due date).
 * It never shrinks: weekends, holidays and summer without assignments change nothing.
 * First count of each stage: 0, 1–2, 3–4, 5–7, 8–11, 12–15, 16+ assignments.
 */
export const STAGE_TASKS = [0, 1, 3, 5, 8, 12, 16] as const;
export const LAST_STAGE = STAGE_TASKS.length - 1;

export function stageFor(done: number): number {
  let s = 0;
  for (let i = 0; i < STAGE_TASKS.length; i++) if (done >= STAGE_TASKS[i]!) s = i;
  return s;
}

/** "1–2 bài", "16+ bài" */
export function stageRange(stage: number): string {
  const from = STAGE_TASKS[stage]!;
  const next = STAGE_TASKS[stage + 1];
  if (next === undefined) return `${from}+ bài`;
  if (next - 1 === from) return `${from} bài`;
  return `${from}–${next - 1} bài`;
}

/** Assignments still needed for the next stage, or null at the last stage. */
export function tasksToNext(done: number): number | null {
  const next = STAGE_TASKS[stageFor(done) + 1];
  return next === undefined ? null : next - done;
}

/** 0..1 progress from the current stage to the next (1 at the last stage). */
export function stageProgress(done: number): number {
  const st = stageFor(done);
  const from = STAGE_TASKS[st]!;
  const next = STAGE_TASKS[st + 1];
  return next === undefined ? 1 : (done - from) / (next - from);
}

/** What the assignment list says about the student's garden. */
export interface AssignmentLike {
  id: string;
  title: string;
  dueAt: string;
  status: "NOT_STARTED" | "IN_PROGRESS" | "DONE" | "CLOSED";
  itemCount: number;
}
export interface Progress {
  done: number; // assignments finished, ever: grows the tree
  streak: number; // finished in a row, counted back from the latest due date; a missed one (CLOSED) resets it
  pending: AssignmentLike[]; // still open, soonest due first: finishing them keeps the streak
}

export function progressOf(items: readonly AssignmentLike[]): Progress {
  const real = items.filter((a) => a.itemCount > 0); // an empty assignment never counts against anyone
  const byDue = [...real].sort((a, b) => Date.parse(a.dueAt) - Date.parse(b.dueAt));
  let streak = 0;
  for (let i = byDue.length - 1; i >= 0; i--) {
    const st = byDue[i]!.status;
    if (st === "DONE") streak++;
    else if (st === "CLOSED") break; // missed before its due date
    // NOT_STARTED / IN_PROGRESS: still open, neither counts nor breaks
  }
  return {
    done: real.filter((a) => a.status === "DONE").length,
    streak,
    pending: byDue.filter((a) => a.status === "NOT_STARTED" || a.status === "IN_PROGRESS"),
  };
}

export const spriteSrc = (id: SpeciesId, stage: number) => `/garden/${id}/${Math.max(0, Math.min(LAST_STAGE, stage))}.webp`;
