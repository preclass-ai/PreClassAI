// Students never read the teacher's lesson plan. Lessons published before the API filtered this (the snapshot is immutable)
// can still carry plan-only text; the student page cleans it so it is gone as soon as the web deploys.

const fold = (s: string) =>
  s.toLowerCase().replace(/đ/g, "d").normalize("NFD").replace(/[̀-ͯ]/g, "");

// CV 5512 scaffolding ("a) Mục tiêu: ...", "Bước 1: GV ...") and in-class prompts needing a picture, video or game.
const SCAFFOLD = /^(?:[a-d]\s*[.)]\s*)?(?:muc tieu|noi dung|san pham|to chuc thuc hien|to chuc)\b|^buoc\s*[1-4]\b/;
const IN_CLASS = /\b(?:gv|giao vien|tranh|video|clip|tro choi|o chu|lat cac)\b/;

/** An instruction block a student cannot act on at home, alone. */
export function isTeacherOnly(text: string): boolean {
  const f = fold(text).replace(/^[*\-•+\s]+/, "").trim();
  return SCAFFOLD.test(f) || IN_CLASS.test(f);
}

/** "Theo giáo án, ..." cites the lesson the student is reading. */
export function studentText(s: string): string {
  return s.replace(/(^|[^\p{L}])([gG])iáo án(?![\p{L}])/gu, (_m, pre: string, g: string) => `${pre}${g === "G" ? "Bài" : "bài"} học`);
}
