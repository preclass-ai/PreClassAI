from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, Response

from app.routers._base import errs, todo
from app.schemas import (
    AssignmentList,
    AuditLogList,
    ClassList,
    LoginRequest,
    ProgressOut,
    UserOut,
)

router = APIRouter()

_PUBLIC: dict[str, Any] = {"security": []}


@router.post(
    "/auth/login", tags=["auth"], operation_id="login", response_model=UserOut, openapi_extra=_PUBLIC,
    summary="Log in (sets the session cookie)",
    description="Sets `preclass_session` (HttpOnly, SameSite=Lax). Rate limited: repeated failures "
    "→ 429 `RATE_LIMITED`. Wrong credentials → 401 `INVALID_CREDENTIALS` (same answer for unknown user).",
    responses=errs(401, 422, (429, "Quá nhiều lần thử (RATE_LIMITED).")),
)
async def login(body: LoginRequest, response: Response) -> UserOut:
    todo()


@router.post("/auth/logout", tags=["auth"], operation_id="logout", status_code=204,
             summary="Log out (revokes the session server-side)", responses=errs(401))
async def logout() -> None:
    todo()


@router.get("/me", tags=["auth"], operation_id="getMe", response_model=UserOut, summary="Current user",
            responses=errs(401))
async def me() -> UserOut:
    todo()


@router.get("/classes", tags=["classes"], operation_id="listClasses", response_model=ClassList,
            summary="Classes the teacher belongs to (TEACHER)", responses=errs(401, 403))
async def list_classes() -> ClassList:
    todo()


@router.get("/classes/{class_id}/assignments", tags=["classes"], operation_id="listClassAssignments",
            response_model=AssignmentList, summary="Assignments of a class (TEACHER of that class)",
            responses=errs(401, 403, 404))
async def list_class_assignments(class_id: UUID) -> AssignmentList:
    todo()


@router.get("/classes/{class_id}/assignments/{assignment_id}/progress", tags=["classes"],
            operation_id="getAssignmentProgress", response_model=ProgressOut,
            summary="First-attempt correct rate per item (TEACHER of that class)",
            responses=errs(401, 403, 404))
async def assignment_progress(class_id: UUID, assignment_id: UUID) -> ProgressOut:
    todo()


@router.get("/admin/audit-logs", tags=["admin"], operation_id="listAuditLogs", response_model=AuditLogList,
            summary="Audit log, newest first (ADMIN, read-only; never contains content)",
            responses=errs(401, 403))
async def audit_logs(action: str | None = Query(None), limit: int = Query(50, ge=1, le=200)) -> AuditLogList:
    todo()
