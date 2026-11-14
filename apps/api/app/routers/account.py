from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import audit
from app.auth import (
    COOKIE,
    CurrentUser,
    create_session,
    current_user,
    login_limiter,
    require_role,
    verify_password,
)
from app.config import get_settings
from app.db import models as m
from app.db.session import get_db
from app.errors import ApiError
from app.routers._base import errs, todo
from app.schemas import (
    AssignmentList,
    AuditLogList,
    AuditLogOut,
    ClassList,
    ClassOut,
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
async def login(
    body: LoginRequest, request: Request, response: Response, db: Annotated[AsyncSession, Depends(get_db)]
) -> UserOut:
    ident = body.identifier.strip().lower()
    key = f"{ident}|{request.client.host if request.client else '-'}"
    login_limiter.check(key)
    user = await db.scalar(
        select(m.AppUser).where(
            or_(func.lower(m.AppUser.email) == ident, func.lower(m.AppUser.login_code) == ident),
            m.AppUser.is_active.is_(True),
        )
    )
    # Same answer and similar timing for unknown user and wrong password.
    if not verify_password(user.password_hash if user else None, body.password) or user is None:
        login_limiter.fail(key)
        audit(db, None, "LOGIN_FAILED", "session")
        await db.commit()
        raise ApiError(401, "INVALID_CREDENTIALS", "Tài khoản hoặc mật khẩu không đúng")
    login_limiter.reset(key)
    token = await create_session(db, user.id)
    audit(db, user.id, "LOGIN", "session")
    out = await _user_out(db, user)
    await db.commit()
    cfg = get_settings()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=cfg.cookie_secure,
                        max_age=cfg.session_ttl_hours * 3600, path="/")
    return out


@router.post("/auth/logout", tags=["auth"], operation_id="logout", status_code=204,
             summary="Log out (revokes the session server-side)", responses=errs(401))
async def logout(
    response: Response, cu: Annotated[CurrentUser, Depends(current_user)], db: Annotated[AsyncSession, Depends(get_db)]
) -> Response:
    await db.execute(update(m.Session).where(m.Session.id == cu.session.id).values(revoked_at=func.now()))
    audit(db, cu.id, "LOGOUT", "session")
    await db.commit()
    out = Response(status_code=204)
    out.delete_cookie(COOKIE, path="/")
    return out


@router.get("/me", tags=["auth"], operation_id="getMe", response_model=UserOut, summary="Current user",
            responses=errs(401))
async def me(
    cu: Annotated[CurrentUser, Depends(current_user)], db: Annotated[AsyncSession, Depends(get_db)]
) -> UserOut:
    return await _user_out(db, cu.user)


@router.get("/classes", tags=["classes"], operation_id="listClasses", response_model=ClassList,
            summary="Classes the teacher belongs to (TEACHER)", responses=errs(401, 403))
async def list_classes(
    cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]
) -> ClassList:
    students = (
        select(m.ClassMember.class_id, func.count().label("n"))
        .where(m.ClassMember.role_in_class == "STUDENT")
        .group_by(m.ClassMember.class_id)
        .subquery()
    )
    rows = await db.execute(
        select(m.Class, func.coalesce(students.c.n, 0))
        .join(m.ClassMember, m.ClassMember.class_id == m.Class.id)
        .outerjoin(students, students.c.class_id == m.Class.id)
        .where(m.ClassMember.user_id == cu.id, m.ClassMember.role_in_class == "TEACHER")
        .order_by(m.Class.code)
    )
    return ClassList(items=[ClassOut(id=c.id, code=c.code, grade=c.grade, student_count=n) for c, n in rows])


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
async def audit_logs(
    _: Annotated[CurrentUser, Depends(require_role("ADMIN"))],
    db: Annotated[AsyncSession, Depends(get_db)],
    action: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
) -> AuditLogList:
    q = select(m.AuditLog).order_by(m.AuditLog.created_at.desc()).limit(limit)
    if action:
        q = q.where(m.AuditLog.action == action)
    rows = (await db.scalars(q)).all()
    return AuditLogList(items=[AuditLogOut(id=r.id, actor_id=r.actor_id, action=r.action,
                                           resource_type=r.resource_type, resource_id=r.resource_id,
                                           metadata=r.meta, created_at=r.created_at) for r in rows])


async def _user_out(db: AsyncSession, user: m.AppUser) -> UserOut:
    class_ids = (await db.scalars(select(m.ClassMember.class_id).where(m.ClassMember.user_id == user.id))).all()
    return UserOut(id=user.id, role=user.role, display_name=user.display_name, email=user.email,
                   login_code=user.login_code, class_ids=list(class_ids))
