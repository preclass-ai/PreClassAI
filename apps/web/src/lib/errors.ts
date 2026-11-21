import { ApiError } from "./api";

/** Short, actionable Vietnamese messages per stable error `code`. */
const MESSAGES: Record<string, string> = {
  NETWORK: "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.",
  UNAUTHENTICATED: "Phiên đăng nhập đã hết. Vui lòng đăng nhập lại.",
  INVALID_CREDENTIALS: "Sai tài khoản hoặc mật khẩu.",
  RATE_LIMITED: "Đăng nhập sai quá nhiều lần. Đợi một lát rồi thử lại.",
  CSRF: "Yêu cầu bị từ chối. Tải lại trang rồi thử lại.",
  FORBIDDEN_ROLE: "Tài khoản của bạn không có quyền thực hiện thao tác này.",
  NOT_FOUND: "Không tìm thấy, hoặc bạn không có quyền xem.",
  VERSION_CONFLICT: "Nội dung vừa được thay đổi ở nơi khác. Đã tải lại bản mới nhất, hãy thử lại.",
  STALE_REVIEW: "Khối này đã thay đổi kể từ lúc bạn xem. Đã tải lại, hãy đọc lại trước khi duyệt.",
  REVISION_LOCKED: "Bản này đã xuất bản nên không sửa được. Hãy tạo bản sửa mới.",
  PUBLISH_BLOCKED: "Chưa đủ điều kiện xuất bản. Xem các mục chưa đạt bên dưới.",
  APPROVE_BLOCKED: "Khối còn lỗi chặn nên chưa duyệt được. Có thể từ chối hoặc yêu cầu sửa.",
  CONFIRM_REQUIRED: "Hãy đánh dấu xác nhận trước khi xuất bản.",
  JOB_ALREADY_RUNNING: "Đang có một lượt sinh nội dung cho bản này.",
  REVISION_NOT_EMPTY: "Bản này đã có nội dung. Chọn \"Thêm vào nội dung hiện có\".",
  NOT_PUBLISHED: "Bản này chưa xuất bản.",
  DRAFT_EXISTS: "Bài đã có một bản nháp đang soạn.",
  ASSIGNMENT_CLOSED: "Bài đã hết hạn nộp.",
  PAST_DUE: "Bài đã hết hạn nộp. Em vẫn xem lại được bài và lời giải.",
  ALREADY_ANSWERED: "Câu này đã được trả lời.",
  CHAT_LIMIT: "Hôm nay em hỏi nhiều rồi, thử tự làm nhé!",
  NOT_ANSWERED: "Em hãy trả lời câu này trước, rồi HABIT AI sẽ giải thích nhé.",
  MESSAGE_REQUIRED: "Em hãy nhập câu hỏi.",
  ANCHOR_NOT_IN_LESSON: "Đoạn nguồn không thuộc các nguồn của bài.",
  WITHDRAWN: "Bài này đã bị giáo viên thu hồi.",
  ALREADY_WITHDRAWN: "Bản này đã được thu hồi trước đó.",
  AI_DISABLED: "Chức năng AI đang tắt hoặc đã hết hạn mức hôm nay. Bạn vẫn có thể soạn thủ công.",
  INVALID_FILE: "Tệp không đọc được. Chỉ nhận tệp .docx, .pdf, .xlsx, .pptx hợp lệ.",
  SOURCE_TOO_LARGE: "Tệp quá lớn để đọc (giới hạn trang, sheet, ô hoặc slide). Hãy chia nhỏ tệp.",
  ACTIVE_CONTENT_REJECTED: "PDF có mã tự chạy hoặc tệp đính kèm nên bị từ chối. Hãy xuất lại PDF thuần.",
  PARSE_TIMEOUT: "Đọc tệp quá lâu nên bị hủy. Hãy thử tệp nhỏ hơn.",
  EXTERNAL_CONTENT_REJECTED: "Tệp có đối tượng nhúng hoặc liên kết ngoài nên bị từ chối.",
  SOURCE_NOT_READABLE: "Nguồn này chưa đọc được nội dung chữ (ví dụ PDF scan). Hãy nạp bản có chữ.",
  FILE_TOO_LARGE: "Tệp lớn hơn 10 MB.",
  MACRO_REJECTED: "Tệp có macro nên bị từ chối.",
  EMPTY_SOURCE: "Nguồn không có nội dung chữ.",
  LICENSE_REQUIRED: "Nguồn dùng chung cho trường phải ghi rõ giấy phép / nguồn gốc.",
  SOURCE_UNCHANGED: "Bản mới giống hệt bản hiện tại.",
  PAYLOAD_INVALID: "Nội dung khối chưa hợp lệ.",
  PARENT_NOT_FOUND: "Khối cha không còn tồn tại.",
  PROVENANCE_INVALID: "Hãy chọn ít nhất một đoạn nguồn, hoặc ghi lý do không có nguồn (không cả hai).",
  GRADE_MISMATCH: "Lớp không cùng khối với bài.",
  INVALID_WINDOW: "Hạn nộp phải sau thời điểm mở bài.",
  VALIDATION_ERROR: "Dữ liệu nhập chưa hợp lệ.",
};

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return MESSAGES[err.code] ?? err.message;
  if (err instanceof Error) return err.message;
  return "Đã có lỗi xảy ra.";
}

export function errorCode(err: unknown): string | null {
  return err instanceof ApiError ? err.code : null;
}
