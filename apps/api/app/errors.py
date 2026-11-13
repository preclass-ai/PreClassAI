"""RFC 9457 problem details with a stable `code`."""

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, title: str, detail: str = "") -> None:
        self.status, self.code, self.title, self.detail = status, code, title, detail


def problem(
    status: int, code: str, title: str, detail: str = "", errors: list[Any] | None = None
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": f"https://preclass.local/problems/{code.lower()}",
        "title": title,
        "status": status,
        "detail": detail,
        "code": code,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type="application/problem+json")


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, exc: ApiError) -> JSONResponse:
        return problem(exc.status, exc.code, exc.title, exc.detail)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        # Never echo submitted values (may contain source/block text): keep loc + type only.
        errs = [{"loc": list(e["loc"]), "type": e["type"]} for e in exc.errors()]
        return problem(422, "VALIDATION_ERROR", "Dữ liệu không hợp lệ", errors=errs)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = "NOT_FOUND" if exc.status_code == 404 else f"HTTP_{exc.status_code}"
        title = "Không tìm thấy" if exc.status_code == 404 else "Lỗi"
        return problem(exc.status_code, code, title)
