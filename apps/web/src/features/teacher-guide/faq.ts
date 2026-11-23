/**
 * What Bé Cầu knows: how a teacher uses PreClass AI. Fixed answers matched by keywords in the browser;
 * nothing is sent to a server or a model.
 */
import { normalize } from "@/features/garden/faq";
import type { TourStep } from "@/features/garden/tour";
import { GUIDE_NAME } from "./globe-mascot";

export type GuideAction = { label: string } & ({ kind: "tour" } | { kind: "theme" } | { kind: "install" } | { kind: "go"; href: string });

export interface GuideAnswer {
  text: string;
  actions?: GuideAction[];
  follow?: string[];
}

interface Entry {
  id: string;
  chip: string;
  keys: string[];
  answer: GuideAnswer;
}

export const START_STEPS = [
  "Thêm nguồn hoặc giáo án của thầy cô (trang Nguồn, Giáo án).",
  "Tạo bài, để AI soạn nháp có gắn nguồn, rồi duyệt từng khối: chỉ khối đã duyệt mới đến tay học sinh.",
  "Xuất bản rồi giao cho lớp, theo dõi lớp làm bài ở bảng Tiến độ học sinh.",
] as const;

export const TEACHER_FAQ: readonly Entry[] = [
  {
    id: "tour",
    chip: "Chỉ mình các phần trên trang này",
    keys: ["huong dan", "tour", "chi minh", "cach dung", "su dung", "trang nay", "co gi", "giup"],
    answer: { text: "Mình dẫn thầy cô đi một vòng: mình chỉ từng phần trên màn hình, bấm “Tiếp” để đi tiếp.", actions: [{ label: "Bắt đầu hướng dẫn", kind: "tour" }] },
  },
  {
    id: "start",
    chip: "Bắt đầu từ đâu?",
    keys: ["bat dau", "tu dau", "lam gi truoc", "quy trinh", "cac buoc", "3 buoc", "ba buoc"],
    answer: {
      text: `Ba bước là xong một bài: 1) ${START_STEPS[0]} 2) ${START_STEPS[1]} 3) ${START_STEPS[2]}`,
      actions: [{ label: "Mở trang Nguồn", kind: "go", href: "/sources" }],
      follow: ["source", "create", "publish"],
    },
  },
  {
    id: "source",
    chip: "Thêm nguồn, giáo án",
    keys: ["nguon", "tai lieu", "docx", "word", "dan van ban", "tai len", "upload", "giao an", "sach giao khoa"],
    answer: {
      text: "Vào trang Nguồn, dán văn bản hoặc tải tệp .docx. Mỗi đoạn được đánh dấu thành điểm neo, nên mọi câu AI soạn đều chỉ về đúng chỗ trong nguồn. Trang Giáo án nhận giáo án DOCX hoặc PDF có chữ để tạo bài cho học sinh làm trước giờ học; thầy cô kiểm tra phần máy đọc được trước khi tạo bài.",
      actions: [{ label: "Mở Nguồn", kind: "go", href: "/sources" }, { label: "Mở Giáo án", kind: "go", href: "/plans" }],
      follow: ["create"],
    },
  },
  {
    id: "create",
    chip: "Tạo bài, AI soạn nháp",
    keys: ["tao bai", "bai moi", "soan", "ai soan", "nhap", "sinh cau hoi", "tao cau hoi"],
    answer: {
      text: "Bấm “Tạo bài mới” ở trang Bài học, chọn nguồn, rồi cho AI soạn nháp. AI chỉ soạn nháp, mỗi khối gắn chỗ trích trong nguồn, và không bao giờ tự duyệt. Thầy cô sửa trực tiếp ở tab “Soạn & nguồn”, phần đang sửa được tự lưu.",
      actions: [{ label: "Tạo bài mới", kind: "go", href: "/lessons/new" }],
      follow: ["review"],
    },
  },
  {
    id: "review",
    chip: "Duyệt nội dung thế nào?",
    keys: ["duyet", "review", "kiem tra", "canh bao", "van de", "duyet lai", "sai"],
    answer: {
      text: "Ở tab Duyệt, đọc từng khối cùng đoạn nguồn bên cạnh, rồi bấm Duyệt hoặc ghi yêu cầu sửa. Khối có cảnh báo (thiếu nguồn, số liệu lệch…) hiện nhãn đỏ. Sửa một khối đã duyệt thì khối đó và các khối phụ thuộc cần duyệt lại.",
      follow: ["publish"],
    },
  },
  {
    id: "publish",
    chip: "Xuất bản và giao bài",
    keys: ["xuat ban", "giao bai", "giao cho lop", "han nop", "mo bai", "publish", "sua han", "huy giao"],
    answer: {
      text: "Khi mọi khối đã duyệt, tab “Xuất bản & giao bài” mở khóa. Xuất bản tạo một bản cố định, rồi chọn lớp, giờ mở và hạn nộp. Muốn sửa bài đã giao thì tạo bản mới; hạn nộp, tên hiển thị hay hủy giao thì sửa ở trang Lớp & bài giao.",
      actions: [{ label: "Mở Lớp & bài giao", kind: "go", href: "/classes" }],
      follow: ["progress"],
    },
  },
  {
    id: "progress",
    chip: "Xem lớp làm đến đâu?",
    keys: ["tien do", "hoan thanh", "bieu do", "lop lam", "theo doi", "giam sat", "bao nhieu em", "thong ke", "muc do"],
    answer: {
      text: "Bảng “Tiến độ học sinh” ở đầu trang Bài học gom mọi lớp: mỗi bài một thanh xanh (đã xong), vàng (đang làm), đỏ (chưa làm). Bài sắp hết hạn mà còn em chưa xong được tô nổi và đưa lên đầu. Bấm tên bài để xem từng câu: bao nhiêu em trả lời, tỉ lệ đúng ngay lần đầu.",
      actions: [{ label: "Mở Lớp & bài giao", kind: "go", href: "/classes" }],
      follow: ["remind", "csv"],
    },
  },
  {
    id: "remind",
    chip: "Nhắc học sinh chưa làm",
    keys: ["nhac", "nhac nho", "nhac hoc sinh", "nhac lop", "chua lam", "zalo", "nhom lop", "thong bao", "doc thuc", "sap het han", "tre han"],
    answer: {
      text: "Mục “Cần nhắc ngay” trong bảng tiến độ liệt kê bài sắp hoặc vừa hết hạn còn em chưa xong. Bấm “Sao chép lời nhắc” là có sẵn một tin ngắn để dán vào nhóm Zalo của lớp.",
      follow: ["csv", "privacy"],
    },
  },
  {
    id: "csv",
    chip: "Biết cụ thể em nào chưa làm?",
    keys: ["csv", "excel", "tai ket qua", "danh sach", "em nao", "ai chua", "diem", "ket qua"],
    answer: {
      text: "Trên trang chỉ có số liệu cả lớp. Bấm “Danh sách (CSV)” hoặc “Tải kết quả (CSV)”: mỗi em một dòng theo mã đăng nhập, có trạng thái làm bài, số câu, số gợi ý và từng câu trả lời. Mở được bằng Excel.",
      follow: ["privacy"],
    },
  },
  {
    id: "habit",
    chip: "HABIT AI giúp học sinh ra sao?",
    keys: ["habit", "ai", "tro ly", "chat", "hoc sinh hoi", "goi y", "phan tich"],
    answer: {
      text: "Trong mỗi câu, học sinh có gợi ý từng bậc và nút “Hỏi HABIT AI”: AI chỉ chỗ số liệu và cách nghĩ, không đưa đáp án. Ở phần tiến độ của từng bài, thầy cô xem nhóm câu hỏi các em hay hỏi và câu nào nên giảng lại.",
      follow: ["progress"],
    },
  },
  {
    id: "install",
    chip: "Cài app lên máy",
    keys: ["cai", "app", "ung dung", "dien thoai", "man hinh chinh", "install", "may tinh"],
    answer: { text: "PreClass AI cài được như ứng dụng trên điện thoại và máy tính, không cần kho ứng dụng. Hướng dẫn từng bước ở cuối trang Bài học.", actions: [{ label: "Xem cách cài", kind: "install" }] },
  },
  {
    id: "privacy",
    chip: "Dữ liệu học sinh",
    keys: ["du lieu", "rieng tu", "bao mat", "ten hoc sinh", "an toan", "privacy"],
    answer: { text: "Trang không hiện tên học sinh và không xếp hạng. Tệp kết quả ghi mã đăng nhập, không có họ tên, và không chứa nội dung trò chuyện với HABIT AI. Môi trường này là thử nghiệm: số liệu chỉ để luyện tập." },
  },
  {
    id: "theme",
    chip: "Giao diện tối",
    keys: ["toi", "dark", "sang", "giao dien", "choi mat", "mau"],
    answer: { text: "Nút Sáng/Tối ở góc trên bên phải. App nhớ lựa chọn của thầy cô.", actions: [{ label: "Đổi sáng/tối", kind: "theme" }] },
  },
];

export const START_CHIPS = ["start", "progress", "remind", "tour"] as const;
const BY_ID = new Map(TEACHER_FAQ.map((e) => [e.id, e]));

export const chipLabel = (id: string) => BY_ID.get(id)?.chip ?? id;
export const answerChip = (id: string): GuideAnswer => BY_ID.get(id)?.answer ?? fallback();

function fallback(): GuideAnswer {
  return { text: `${GUIDE_NAME} chưa rõ câu này. Thầy cô thử chọn một chủ đề dưới đây, hoặc hỏi ngắn gọn hơn, ví dụ “giao bài”, “nhắc học sinh”.`, follow: ["start", "progress", "publish", "csv"] };
}

/** Best keyword match; longer keys weigh more so "chua lam" beats "lam". */
export function answerGuide(question: string): GuideAnswer {
  const q = ` ${normalize(question)} `;
  let best: Entry | null = null;
  let score = 0;
  for (const e of TEACHER_FAQ) {
    const s = e.keys.reduce((n, k) => (q.includes(` ${k} `) || q.includes(` ${k}`) ? n + k.length : n), 0);
    if (s > score) {
      score = s;
      best = e;
    }
  }
  return best ? best.answer : fallback();
}

export type TeacherTour = "lessons" | "classes" | "page";
export function tourFor(path: string): TeacherTour {
  if (path === "/lessons") return "lessons";
  if (path === "/classes") return "classes";
  return "page";
}

export function teacherTourSteps(name: TeacherTour): TourStep[] {
  const hello = { title: `Chào thầy cô, mình là ${GUIDE_NAME}!`, text: "Mình là quả địa cầu của PreClass AI. Mình dẫn thầy cô xem nhanh trang này nhé." };
  const mascot = { target: "teacher-guide", title: "Cần gì cứ bấm mình", text: "Mình ở góc này: hỏi cách tạo bài, giao bài, theo dõi hay nhắc lớp, mình chỉ ngay và mở đúng trang." };
  if (name === "lessons") {
    return [
      hello,
      { target: "nav", title: "Bốn trang chính", text: "Bài học: soạn và duyệt. Nguồn: tài liệu gốc. Giáo án: nạp giáo án để tạo bài làm trước giờ học. Lớp & bài giao: giao bài, sửa hạn, xem kết quả." },
      { target: "progress", title: "Tiến độ học sinh", text: "Mỗi bài đang giao là một thanh: xanh đã xong, vàng đang làm, đỏ chưa làm. Bài sắp hết hạn còn em chưa xong được đưa lên đầu, kèm lời nhắc sao chép sẵn để gửi lớp." },
      { target: "new-lesson", title: "Tạo bài mới", text: "Chọn nguồn, để AI soạn nháp có gắn chỗ trích, rồi thầy cô duyệt từng khối." },
      { target: "lesson-table", title: "Danh sách bài học", text: "Cột “Tiến độ duyệt” cho biết còn bao nhiêu khối chưa duyệt, có vấn đề hay cần duyệt lại." },
      { target: "install", title: "Cài lên máy", text: "Cài PreClass AI như ứng dụng để mở một chạm trên điện thoại hay máy tính." },
      { target: "theme", title: "Sáng hay tối", text: "Đổi giao diện cho dễ nhìn, app nhớ lựa chọn." },
      mascot,
    ];
  }
  if (name === "classes") {
    return [
      { title: "Lớp & bài giao", text: `${GUIDE_NAME} chỉ nhanh trang theo dõi lớp nhé.` },
      { target: "class-tabs", title: "Chọn lớp", text: "Mỗi thẻ là một lớp, kèm số học sinh." },
      { target: "progress", title: "Tiến độ của lớp", text: "Bài nào lớp làm đến đâu, bài nào cần nhắc. Bấm “Sao chép lời nhắc” để gửi nhóm lớp, hoặc tải danh sách để biết em nào." },
      { target: "assignment-list", title: "Bài đã giao", text: "Sửa hạn, đổi tên hiển thị, hủy giao, hoặc bấm “Xem tiến độ và câu hỏi” để xem từng câu và gợi ý giảng lại." },
      mascot,
    ];
  }
  return [
    { title: `${GUIDE_NAME} đây!`, text: "Trang này mình chưa có hướng dẫn riêng. Thầy cô bấm vào mình để hỏi cách làm bất cứ bước nào nhé." },
    { target: "nav", title: "Bốn trang chính", text: "Bài học, Nguồn, Giáo án, Lớp & bài giao: luôn ở thanh trên cùng." },
    mascot,
  ];
}
