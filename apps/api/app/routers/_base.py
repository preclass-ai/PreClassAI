from typing import Any, NoReturn

from app.errors import ApiError
from app.schemas import Problem


def todo() -> NoReturn:
    """Contract-only handler (phase 3). Replaced by real services in phases 4-9."""
    raise ApiError(501, "NOT_IMPLEMENTED", "Chưa triển khai", "Endpoint đang ở giai đoạn hợp đồng (v0).")


_DESC = {
    401: "Chưa đăng nhập hoặc phiên hết hạn (UNAUTHENTICATED).",
    403: "Sai vai trò (FORBIDDEN_ROLE).",
    404: "Không tìm thấy, hoặc tài nguyên của người/lớp khác (NOT_FOUND). Không phân biệt hai trường hợp.",
    409: "Xung đột trạng thái hoặc phiên bản.",
    410: "Đã thu hồi (WITHDRAWN).",
    422: "Dữ liệu không hợp lệ (VALIDATION_ERROR).",
    503: "AI đang tắt (AI_DISABLED).",
}


def errs(*codes: int | tuple[int, str]) -> dict[int | str, dict[str, Any]]:
    """Problem+json error responses; a tuple overrides the description (e.g. the specific 409 codes)."""
    out: dict[int | str, dict[str, Any]] = {}
    for c in codes:
        status, desc = (c, _DESC[c]) if isinstance(c, int) else c
        out[status] = {"model": Problem, "description": desc}
    return out
