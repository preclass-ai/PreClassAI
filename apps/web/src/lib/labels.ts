import type { Schemas } from "./api";

export type ReviewStatus = Schemas["BlockOut"]["reviewStatus"];
export type BlockKind = Schemas["BlockOut"]["kind"];
export type Transformation = Schemas["BlockOut"]["transformation"];
export type RevisionState = Schemas["RevisionOut"]["state"];

export const REVIEW_STATUS: Record<ReviewStatus, { label: string; tone: Tone }> = {
  UNREVIEWED: { label: "Chưa kiểm", tone: "neutral" },
  AUTO_CHECKED: { label: "Máy đã kiểm", tone: "info" },
  FLAGGED: { label: "Có vấn đề", tone: "danger" },
  APPROVED: { label: "Đã duyệt", tone: "success" },
  REVIEW_AGAIN: { label: "Cần duyệt lại", tone: "warning" },
  REJECTED: { label: "Đã từ chối", tone: "danger" },
};

export const REVISION_STATE: Record<RevisionState, { label: string; tone: Tone }> = {
  DRAFT: { label: "Bản nháp", tone: "neutral" },
  IN_REVIEW: { label: "Đang duyệt", tone: "info" },
  PUBLISHED: { label: "Đã xuất bản", tone: "success" },
  SUPERSEDED: { label: "Đã thay thế", tone: "neutral" },
};

export const KIND: Record<BlockKind, string> = {
  heading: "Tiêu đề",
  paragraph: "Đoạn văn",
  data_fact: "Số liệu",
  instruction: "Hướng dẫn",
  worksheet_item: "Câu hỏi",
  option: "Phương án",
  answer_key: "Đáp án",
  explanation: "Giải thích",
  card_front: "Thẻ – mặt trước",
  card_back: "Thẻ – mặt sau",
};

export const TRANSFORMATION: Record<Transformation, string> = {
  ORIGINAL: "Nguyên văn",
  PARAPHRASED: "Diễn đạt lại",
  SYNTHESISED: "Tổng hợp",
  AI_PROPOSED: "AI đề xuất",
  TEACHER_AUTHORED: "GV tự viết",
};

export const SKILL: Record<Schemas["WorksheetItemPayload"]["skill"], string> = {
  READ_TABLE: "Đọc bảng",
  COMPARE: "So sánh",
  CALCULATE: "Tính toán",
  EXPLAIN: "Giải thích",
};

export const ITEM_TYPE: Record<Schemas["WorksheetItemPayload"]["itemType"], string> = {
  MCQ: "Trắc nghiệm",
  SHORT: "Tự luận ngắn",
  NUMERIC: "Tính số",
};

export const RELATION: Record<Schemas["LinkIn"]["relation"], string> = {
  derived_from: "Suy ra từ",
  quotes: "Trích",
  supports: "Minh chứng",
};

export const CHECK: Record<Schemas["PublishCheckItem"]["code"], string> = {
  ALL_APPROVED: "Mọi khối đã được duyệt",
  NO_BLOCKERS: "Không còn lỗi chặn",
  SOURCES_VALID: "Nguồn của các khối còn hợp lệ",
  HAS_ITEMS: "Có ít nhất một câu hỏi",
};

export const OPERATION: Record<string, string> = {
  GENERATE: "AI sinh nội dung",
  EDIT: "Sửa",
  REGENERATE: "Sinh lại",
  SOURCE_REPLACED: "Đổi nguồn",
  REVIEW: "Duyệt",
  PUBLISH: "Xuất bản",
  WITHDRAW: "Thu hồi",
};

export const ACTOR: Record<string, string> = { AI: "AI", TEACHER: "Giáo viên", SYSTEM: "Hệ thống" };

export type Tone = "neutral" | "info" | "success" | "warning" | "danger";
