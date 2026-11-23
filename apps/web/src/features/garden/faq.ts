/**
 * What the mascot knows outside a question: how to use PreClass. Fixed answers, matched by keywords on the client.
 * Nothing is sent to a server or an AI model here; questions about the lesson itself go to HABIT AI inside each question.
 */
import { stageFor, stageRange, STAGE_TASKS, tasksToNext, type Progress, type Species } from "./species";

export type FaqAction = "tour" | "picker" | "theme" | "selfstudy";

export interface FaqContext {
  species: Species;
  progress: Progress | null;
  onAssignment: boolean; // the student is on an assignment page
}

export interface FaqAnswer {
  text: string;
  actions?: { label: string; action: FaqAction }[];
  follow?: string[]; // chip ids to suggest next
}

interface Entry {
  id: string;
  chip: string; // label on the quick button
  keys: string[]; // normalized (no diacritics) keywords
  answer: (c: FaqContext) => FaqAnswer;
}

/** "Hỏi HABIT AI ở đâu?" -> "hoi habit ai o dau" */
export function normalize(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .replace(/đ/g, "d")
    .replace(/[^a-z0-9 ]+/g, " ")
    .replace(/\s+/g, " ")
    .trim();
}

export const FAQ: readonly Entry[] = [
  {
    id: "tour",
    chip: "Hướng dẫn mình dùng app",
    keys: ["huong dan", "tour", "chi minh", "cach dung", "su dung", "bat dau tu dau", "lam sao dung", "giup"],
    answer: () => ({
      text: "Mình dẫn em đi một vòng nhé: mình sẽ chỉ từng phần trên màn hình này, em bấm “Tiếp” để đi tiếp.",
      actions: [{ label: "Bắt đầu hướng dẫn", action: "tour" }],
    }),
  },
  {
    id: "do",
    chip: "Làm bài thế nào?",
    keys: ["lam bai", "bai tap", "cau hoi", "tra loi", "chon dap an", "bai duoc giao", "bat dau"],
    answer: (c) => ({
      text: c.onAssignment
        ? "Em đọc nội dung bài, rồi làm từng câu: chọn hoặc gõ câu trả lời và bấm Nộp. Nếu bài có phần ôn, em có thể ôn nhanh vài thẻ trước (không tính điểm)."
        : "Ở trang “Bài của em”, bấm vào một thẻ bài để mở. Trong bài: đọc nội dung, làm từng câu rồi bấm Nộp. Thẻ ghi hạn nộp và số câu em đã làm.",
      follow: ["hint", "ai", "submit"],
    }),
  },
  {
    id: "hint",
    chip: "Gợi ý dùng sao?",
    keys: ["goi y", "hint", "bong den", "bac", "luot goi y", "het goi y"],
    answer: () => ({
      text: "Dưới mỗi câu chưa làm có nút gợi ý. Mỗi lần bấm, gợi ý cụ thể hơn một bậc, và mỗi câu có số lượt giới hạn. Thử tự nghĩ trước rồi mới mở gợi ý nhé, như vậy em nhớ lâu hơn.",
      follow: ["ai", "submit"],
    }),
  },
  {
    id: "ai",
    chip: "Hỏi HABIT AI ở đâu?",
    keys: ["habit", "ai", "tro ly", "hoi bai", "chat", "giai thich", "hoi ve bai"],
    answer: (c) => ({
      text: `Trong mỗi câu có nút “Hỏi HABIT AI”. Bấm vào đó là ${c.species.mascot} sẽ vào khung trò chuyện, cùng em suy nghĩ về đúng câu ấy, chỉ chỗ số liệu và cách làm. Mình không đưa đáp án đâu nha. Sau khi nộp, nút đổi thành “HABIT AI giải thích” để xem lại lời giải.`,
      follow: ["hint", "privacy"],
    }),
  },
  {
    id: "study",
    chip: "Học trước sao cho hiểu?",
    keys: ["phuong phap", "hoc truoc", "tu hoc", "doc truoc", "cach hoc truoc", "hoc sao", "hoc the nao", "sq3r", "kwl", "feynman", "pomodoro", "cornell", "hay quen", "mau quen", "nho lau", "hoc thuoc", "doc hieu", "bang so lieu", "bieu do", "ky nang", "ki nang"],
    answer: (c) => ({
      text: `${c.species.mascot} biết vài cách học trước hay lắm: SQ3R và bảng KWL để đọc bài có mục đích, 5 bước đọc bảng số liệu, kĩ thuật Feynman, tự kiểm tra, ôn ngắt quãng và Pomodoro. Vào tab “Tự học”, chọn điều em hay gặp khó, rồi bấm “Học cùng ${c.species.mascot}” là mình kèm em từng bước.`,
      actions: [{ label: "Mở Tự học", action: "selfstudy" }],
      follow: ["do", "focus"],
    }),
  },
  {
    id: "submit",
    chip: "Nộp bài và xem lời giải",
    keys: ["nop", "dap an", "loi giai", "lam lai", "sai", "dung chua", "ket qua", "diem"],
    answer: () => ({
      text: "Mỗi câu chỉ nộp một lần, để thầy cô biết em hiểu đến đâu ngay từ lần đầu. Nộp xong em thấy đáp án và lời giải thầy cô đã duyệt. Muốn luyện thêm thì bấm “Làm lại”: lượt luyện không đổi kết quả thầy cô thấy.",
      follow: ["streak"],
    }),
  },
  {
    id: "streak",
    chip: "Chuỗi bài là gì?",
    keys: ["chuoi", "streak", "lua", "lien tiep", "ngay lien tiep", "mat chuoi", "nghi le", "nghi he", "cuoi tuan", "tuoi cay"],
    answer: (c) => ({
      text:
        "Mỗi bài thầy cô giao mà em làm xong hết các câu trước hạn nộp, chuỗi tăng thêm 1. Để một bài hết hạn mà chưa xong thì chuỗi bắt đầu lại. Cuối tuần, ngày lễ hay nghỉ hè không có bài thì chuỗi vẫn giữ nguyên, em cứ yên tâm nghỉ." +
        (c.progress ? ` Hiện em có chuỗi ${c.progress.streak} bài liên tiếp.` : ""),
      follow: ["grow"],
    }),
  },
  {
    id: "grow",
    chip: "Cây lớn thế nào?",
    keys: ["cay lon", "giai doan", "lon len", "cay", "khu vuon", "vuon", "no hoa", "ket trai"],
    answer: (c) => {
      const s = c.species;
      const list = s.stages.map((n, i) => `${n} (${stageRange(i)})`).join(", ");
      const now = !c.progress ? "" : (() => {
        const st = stageFor(c.progress.done);
        const left = tasksToNext(c.progress.done);
        return ` Bây giờ mình đang ở giai đoạn “${s.stages[st]}”${left !== null ? `, còn ${left} bài nữa là tới “${s.stages[st + 1]}”` : ", lớn hết cỡ rồi"}.`;
      })();
      return { text: `${s.name} lớn theo tổng số bài em đã làm xong, và không bao giờ bị tụt, kể cả khi đứt chuỗi. Có ${STAGE_TASKS.length} giai đoạn: ${list}.${now}`, follow: ["change"] };
    },
  },
  {
    id: "change",
    chip: "Đổi giống cây",
    keys: ["doi cay", "doi giong", "giong cay", "chon cay", "hat giong", "doi mascot", "doi ban"],
    answer: () => ({
      text: "Em đổi giống cây được bất cứ lúc nào ở khu vườn trên trang “Bài của em”. Số bài em đã làm xong vẫn giữ nguyên nên cây mới sẽ ở đúng giai đoạn của em.",
      actions: [{ label: "Đổi giống cây", action: "picker" }],
    }),
  },
  {
    id: "theme",
    chip: "Chế độ sáng / tối",
    keys: ["toi", "sang", "dark", "light", "giao dien", "mau nen", "ban dem", "theme", "choi mat"],
    answer: () => ({
      text: "Nút Sáng/Tối nằm ở thanh trên cùng, cạnh tên em. Lần đầu app theo cài đặt của máy; em bấm một lần là app nhớ lựa chọn của em.",
      actions: [{ label: "Đổi ngay", action: "theme" }],
    }),
  },
  {
    id: "focus",
    chip: "Chế độ tập trung",
    keys: ["tap trung", "focus", "hen gio", "cach hoc", "tung cau", "chia nho"],
    answer: () => ({
      text: "Trong bài có khung “Cách học hôm nay”: em chọn kiểu gợi ý em thích, bật “Chế độ tập trung” để làm từng câu một, và hẹn giờ nếu muốn. Đây là lựa chọn của em, không ảnh hưởng điểm.",
    }),
  },
  {
    id: "badge",
    chip: "Huy hiệu",
    keys: ["huy hieu", "badge", "tu luc", "kien tri", "tham hiem", "phan thuong"],
    answer: () => ({
      text: "Có 3 huy hiệu: Tự lực (đúng ngay lần đầu, không cần gợi ý), Kiên trì (học 3 ngày liên tiếp) và Thám hiểm (đọc phần nguồn rồi làm đúng). Huy hiệu hiện ở thanh thói quen phía trên mỗi bài.",
    }),
  },
  {
    id: "review",
    chip: "Thẻ ôn là gì?",
    keys: ["the on", "on tap", "on nhanh", "flashcard", "xem lai phan on"],
    answer: () => ({
      text: "Một số bài có phần ôn nhanh bằng thẻ trước khi làm. Ôn không tính điểm. Đang làm câu, em vẫn có thể bấm “Xem lại phần ôn”, và HABIT AI đôi khi gợi ý mở đúng thẻ cần xem.",
    }),
  },
  {
    id: "due",
    chip: "Hạn nộp",
    keys: ["han nop", "het han", "deadline", "tre han", "qua han"],
    answer: () => ({
      text: "Hạn nộp ghi trên thẻ bài và ở đầu trang bài. Hết hạn thì không nộp được nữa, nhưng em vẫn xem lại bài được.",
    }),
  },
  {
    id: "privacy",
    chip: "Dữ liệu của mình",
    keys: ["du lieu", "rieng tu", "thong tin ca nhan", "bao mat", "ai thay", "thay co thay"],
    answer: () => ({
      text: "Đừng gõ thông tin cá nhân (họ tên đầy đủ, số điện thoại, địa chỉ) vào khung hỏi. Lựa chọn cây và hướng dẫn chỉ lưu trên trình duyệt này, mình không gửi đi đâu cả.",
    }),
  },
  {
    id: "logout",
    chip: "Đăng xuất",
    keys: ["dang xuat", "thoat", "logout", "doi tai khoan"],
    answer: () => ({ text: "Nút “Đăng xuất” ở góc phải thanh trên cùng, cạnh tên em." }),
  },
];

const BY_ID = Object.fromEntries(FAQ.map((e) => [e.id, e]));
export const START_CHIPS = ["tour", "do", "study", "ai", "streak"] as const;
export const chipLabel = (id: string) => BY_ID[id]?.chip ?? id;

const GREET = ["chao", "hello", "hi", "xin chao", "alo", "hey"];
const WHO = ["ban la ai", "la ai", "ten gi", "ten ban"];
const THANKS = ["cam on", "thanks", "thank", "cam on nha"];

/** Best entry for a free-text question: the one with the most (and longest) keyword hits. */
export function answerFaq(question: string, c: FaqContext): FaqAnswer {
  const q = ` ${normalize(question)} `;
  const has = (k: string) => q.includes(` ${k} `) || (k.includes(" ") && q.includes(k));
  if (WHO.some(has)) {
    return {
      text: `Mình là ${c.species.mascot}, ${c.species.name.toLowerCase()} em đã gieo. Mình lớn lên theo số bài em làm xong, chỉ em cách dùng PreClass, và khi em bấm “Hỏi HABIT AI” trong một câu thì mình vào cùng suy nghĩ với em.`,
      follow: ["tour", "grow"],
    };
  }
  if (THANKS.some(has)) return { text: "Không có gì nha! Cần gì cứ bấm vào mình." };
  let best: Entry | null = null;
  let score = 0;
  for (const e of FAQ) {
    const s = e.keys.reduce((n, k) => (has(k) ? n + k.length : n), 0);
    if (s > score) {
      best = e;
      score = s;
    }
  }
  if (best) return best.answer(c);
  if (GREET.some(has)) return { text: `${c.species.hello} Em muốn mình giúp gì?`, follow: [...START_CHIPS] };
  return {
    text: "Mình chỉ trả lời về cách dùng PreClass thôi. Câu hỏi về nội dung bài, em bấm “Hỏi HABIT AI” ngay trong câu đó, mình sẽ vào giúp. Hay em chọn một câu bên dưới nhé:",
    follow: [...START_CHIPS],
  };
}

export function answerChip(id: string, c: FaqContext): FaqAnswer {
  return BY_ID[id]?.answer(c) ?? answerFaq(id, c);
}
