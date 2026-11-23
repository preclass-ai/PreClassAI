/**
 * "Tự học": study methods a student can use before class. Fixed content, written for Grade 10–12 Geography
 * (tables, charts, maps). Each method names where it comes from so a teacher can check it.
 */
export type Group = "preread" | "deep" | "memory" | "focus";

export const GROUPS: Record<Group, { label: string; hint: string }> = {
  preread: { label: "Đọc trước", hint: "Trước giờ lên lớp" },
  deep: { label: "Hiểu sâu", hint: "Khi bài khó" },
  memory: { label: "Ghi nhớ", hint: "Để không quên" },
  focus: { label: "Tập trung", hint: "Khi dễ xao nhãng" },
};

export interface Method {
  id: string;
  name: string;
  short: string; // one line under the name
  group: Group;
  minutes: string;
  origin: string;
  why: string;
  steps: { title: string; text: string }[];
  geo: string; // how it looks with a Geography lesson
  timer?: boolean;
}

export const METHODS: readonly Method[] = [
  {
    id: "sq3r",
    name: "SQ3R",
    short: "Lướt, đặt câu hỏi, đọc, nhắc lại, ôn lại",
    group: "preread",
    minutes: "15–20 phút",
    origin: "Francis P. Robinson, 1946",
    why: "Đặt câu hỏi trước khi đọc giúp em đọc có mục đích, không trôi chữ.",
    steps: [
      { title: "S · Survey (lướt)", text: "Lướt tên bài, các đề mục, hình, bảng, biểu đồ và câu hỏi cuối bài. Chưa đọc kĩ." },
      { title: "Q · Question (hỏi)", text: "Biến mỗi đề mục thành một câu hỏi. Ví dụ “Phân bố dân cư” thành “Dân cư phân bố ra sao, vì sao?”." },
      { title: "R · Read (đọc)", text: "Đọc từng phần để tìm câu trả lời cho câu hỏi của mình. Gạch chân số liệu then chốt." },
      { title: "R · Recite (nhắc lại)", text: "Gấp tài liệu, tự trả lời bằng lời của em, nói thành tiếng hoặc viết vài dòng." },
      { title: "R · Review (ôn lại)", text: "Xem lại các câu hỏi và câu trả lời. Ôn lại sau 1 ngày và trước giờ kiểm tra." },
    ],
    geo: "Với bài Địa lí: lướt tên bảng, biểu đồ, lược đồ trước; câu hỏi tốt thường có “ở đâu, bao nhiêu, vì sao”.",
  },
  {
    id: "kwl",
    name: "Bảng KWL",
    short: "Đã biết gì, muốn biết gì, học được gì",
    group: "preread",
    minutes: "10 phút",
    origin: "Donna Ogle, 1986",
    why: "Nối bài mới với điều em đã biết, nên nhớ lâu hơn và thấy rõ mình còn thiếu gì.",
    steps: [
      { title: "K · Know", text: "Trước khi đọc, ghi 3–5 điều em đã biết về chủ đề." },
      { title: "W · Want", text: "Ghi 2–3 câu hỏi em muốn biết sau bài này." },
      { title: "L · Learned", text: "Làm bài xong, ghi điều em học được và đánh dấu câu hỏi nào đã có lời giải." },
    ],
    geo: "Ví dụ bài rừng nhiệt đới: K “rừng có ở Tây Nguyên”, W “mỗi năm mất bao nhiêu ha?”, L ghi số liệu từ bảng.",
  },
  {
    id: "chart",
    name: "Đọc bảng số liệu, biểu đồ",
    short: "5 bước đọc số liệu Địa lí không bị rối",
    group: "deep",
    minutes: "5–10 phút mỗi bảng",
    origin: "Kĩ năng Địa lí THPT (đọc, so sánh, tính, nhận xét)",
    why: "Phần lớn câu hỏi trong bài cần đọc đúng bảng: đơn vị, năm, rồi mới so sánh.",
    steps: [
      { title: "Đọc tên và đơn vị", text: "Bảng nói về gì, ở đâu, năm nào, đơn vị là %, nghìn người hay triệu tấn?" },
      { title: "Tìm lớn nhất, nhỏ nhất", text: "Khoanh giá trị cao nhất, thấp nhất và nơi có thay đổi lớn nhất." },
      { title: "So sánh", text: "So giữa các vùng, hoặc giữa các năm. Gấp mấy lần, hơn kém bao nhiêu?" },
      { title: "Tính khi cần", text: "Tỉ trọng = phần / tổng × 100. Tăng bao nhiêu % = (sau − trước) / trước × 100." },
      { title: "Nhận xét có số liệu", text: "Viết: ý chung trước, rồi dẫn chứng bằng số, cuối cùng nêu nơi khác biệt." },
    ],
    geo: "Đây đúng là các kĩ năng trong câu hỏi PreClass: đọc bảng, so sánh, tính toán, giải thích.",
  },
  {
    id: "feynman",
    name: "Kĩ thuật Feynman",
    short: "Giảng lại cho người khác bằng lời thật đơn giản",
    group: "deep",
    minutes: "10 phút",
    origin: "Theo cách học của nhà vật lí Richard Feynman",
    why: "Chỗ em giảng bị vấp chính là chỗ em chưa hiểu.",
    steps: [
      { title: "Chọn một ý", text: "Ví dụ “vì sao Đồng bằng sông Hồng đông dân”." },
      { title: "Giảng như cho em lớp dưới", text: "Viết hoặc nói ra, không dùng từ khó, có ví dụ." },
      { title: "Tìm chỗ vấp", text: "Chỗ nào nói không trơn, quay lại tài liệu đọc đúng chỗ đó." },
      { title: "Giảng lại gọn hơn", text: "Rút còn 3–4 câu, có một số liệu làm dẫn chứng." },
    ],
    geo: "Hợp với câu hỏi “giải thích”: nguyên nhân tự nhiên trước, kinh tế, xã hội sau.",
  },
  {
    id: "cornell",
    name: "Ghi chép Cornell",
    short: "Chia trang ba phần: ghi chép, câu hỏi, tóm tắt",
    group: "deep",
    minutes: "Trong lúc đọc",
    origin: "Walter Pauk, Đại học Cornell",
    why: "Vở tự biến thành bộ câu hỏi để ôn, không phải chép lại.",
    steps: [
      { title: "Chia trang", text: "Cột trái hẹp (từ khóa, câu hỏi), cột phải rộng (ghi chép), dải dưới cùng (tóm tắt)." },
      { title: "Ghi ở cột phải", text: "Ý chính và số liệu, viết ngắn, không chép nguyên văn." },
      { title: "Đặt câu hỏi ở cột trái", text: "Mỗi khối ghi chép một câu hỏi hoặc từ khóa." },
      { title: "Tóm tắt 2–3 câu", text: "Ở dải dưới: bài này nói gì nhất." },
      { title: "Ôn bằng cách che", text: "Che cột phải, nhìn câu hỏi bên trái và tự trả lời." },
    ],
    geo: "Cột trái hợp để ghi tên vùng hoặc tên bảng, cột phải ghi số liệu nổi bật.",
  },
  {
    id: "recall",
    name: "Tự kiểm tra",
    short: "Gấp sách lại và tự hỏi, thay vì đọc đi đọc lại",
    group: "memory",
    minutes: "5–10 phút",
    origin: "Hiệu ứng kiểm tra (retrieval practice)",
    why: "Mỗi lần cố nhớ lại là một lần trí nhớ chắc thêm; đọc lại chỉ tạo cảm giác quen.",
    steps: [
      { title: "Gấp tài liệu", text: "Không nhìn bài." },
      { title: "Viết ra điều nhớ được", text: "Ý chính, số liệu, tên vùng. Sai cũng được." },
      { title: "Đối chiếu", text: "Mở bài ra, đánh dấu chỗ thiếu hoặc sai." },
      { title: "Làm lại phần sai", text: "Trong PreClass, bấm “Làm lại” ở câu chưa đúng để luyện thêm." },
    ],
    geo: "Thẻ ôn nhanh đầu bài trong PreClass chính là một lượt tự kiểm tra (không tính điểm).",
  },
  {
    id: "spaced",
    name: "Ôn ngắt quãng",
    short: "Ôn ít mà nhiều lần: sau 1, 3, 7 ngày",
    group: "memory",
    minutes: "5 phút mỗi lần",
    origin: "Đường cong quên lãng (Hermann Ebbinghaus)",
    why: "Ôn đúng lúc sắp quên giúp nhớ lâu hơn ôn dồn một buổi.",
    steps: [
      { title: "Ngay sau khi học", text: "Tóm tắt 3 ý chính." },
      { title: "Sau 1 ngày", text: "Tự kiểm tra 5 phút." },
      { title: "Sau 3 ngày", text: "Làm lại những câu từng sai." },
      { title: "Sau 7 ngày", text: "Ôn nhanh trước tiết học hoặc bài kiểm tra." },
    ],
    geo: "Mở lại bài đã xong trong “Bài của em”, phần lời giải thầy cô đã duyệt vẫn còn đó.",
  },
  {
    id: "pomodoro",
    name: "Pomodoro",
    short: "25 phút tập trung, 5 phút nghỉ",
    group: "focus",
    minutes: "25 + 5 phút",
    origin: "Francesco Cirillo, cuối những năm 1980",
    why: "Chia nhỏ thời gian làm việc bắt đầu dễ hơn và ít xao nhãng hơn.",
    steps: [
      { title: "Chọn một việc", text: "Ví dụ: làm xong 4 câu đầu của bài được giao." },
      { title: "Cất điện thoại, bấm giờ 25 phút", text: "Chỉ làm đúng việc đó." },
      { title: "Nghỉ 5 phút", text: "Đứng dậy, uống nước, không lướt mạng." },
      { title: "Sau 4 lượt, nghỉ dài", text: "15–30 phút." },
    ],
    geo: "Một bài PreClass 7–10 câu thường vừa một lượt Pomodoro.",
    timer: true,
  },
];

export interface Problem {
  id: string;
  label: string;
  methods: string[];
}

export const PROBLEMS: readonly Problem[] = [
  { id: "start", label: "Không biết đọc bài từ đâu", methods: ["sq3r", "kwl"] },
  { id: "forget", label: "Đọc xong là quên", methods: ["recall", "spaced"] },
  { id: "chart", label: "Gặp bảng số liệu, biểu đồ là rối", methods: ["chart"] },
  { id: "vague", label: "Hiểu lơ mơ, khó giải thích lại", methods: ["feynman", "cornell"] },
  { id: "focus", label: "Khó tập trung, hay cầm điện thoại", methods: ["pomodoro"] },
];

export const METHOD_BY_ID = new Map(METHODS.map((m) => [m.id, m]));
