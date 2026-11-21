"""Anonymous survey access (off unless GUEST_ACCESS_ENABLED=true) and the survey data export."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app import guest as svc
from app.audit import audit
from app.auth import COOKIE, CurrentUser, create_session, require_role
from app.config import get_settings
from app.db.session import get_db
from app.habit import chat_stats as habit_stats
from app.routers._base import errs
from app.routers.account import _user_out
from app.schemas import AuthConfig, GuestOut, GuestRequest, GuestResumeRequest, SurveyStats

router = APIRouter()
_PUBLIC: dict[str, Any] = {"security": []}
Db = Annotated[AsyncSession, Depends(get_db)]


def _ip(request: Request) -> str:
    return request.client.host if request.client else "-"  # real client IP behind the proxy (uvicorn --proxy-headers)


async def _start(db: AsyncSession, response: Response, user: Any, lesson_key: str | None) -> GuestOut:
    cfg = get_settings()
    token = await create_session(db, user.id, ttl_hours=cfg.guest_session_days * 24)
    out = GuestOut(user=await _user_out(db, user), survey_code=user.survey_code,
                   assignment_id=await svc.assignment_for_lesson(db, lesson_key))
    await db.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", secure=cfg.cookie_secure,
                        max_age=cfg.guest_session_days * 86400, path="/")
    return out


@router.get("/auth/config", tags=["auth"], operation_id="getAuthConfig", response_model=AuthConfig, openapi_extra=_PUBLIC,
            summary="Public sign-in options (is anonymous guest access on?)")
async def auth_config() -> AuthConfig:
    return AuthConfig(guest_enabled=get_settings().guest_access_enabled, chat_enabled=get_settings().chat_enabled,
                      personalization_enabled=get_settings().personalization_enabled)


@router.post("/auth/guest", tags=["auth"], operation_id="createGuest", status_code=201, response_model=GuestOut,
             openapi_extra=_PUBLIC, summary="Start as an anonymous guest (survey)",
             description="Creates a STUDENT account with no name/e-mail/password, joins the survey class, sets the session "
             "cookie (14 days). Returns the survey code to write on the questionnaire. 404 when guest access is off; "
             "429 `RATE_LIMITED` per client IP; 503 when the survey class is missing or `GUEST_MAX_ACTIVE` is reached.",
             responses=errs(404, 422, (429, "RATE_LIMITED."), (503, "GUEST_NOT_CONFIGURED / GUEST_CAPACITY.")))
async def create_guest(body: GuestRequest, request: Request, response: Response, db: Db) -> GuestOut:
    svc.require_enabled()
    user = await svc.create_guest(db, _ip(request))
    return await _start(db, response, user, body.lesson_key)


@router.post("/auth/guest/resume", tags=["auth"], operation_id="resumeGuest", response_model=GuestOut,
             openapi_extra=_PUBLIC, summary="Come back as the same guest with the survey code",
             description="For a lost cookie / another device. 5 wrong codes per IP per 15 minutes → 429 `RATE_LIMITED`.",
             responses=errs(404, 422, (429, "RATE_LIMITED.")))
async def resume_guest(body: GuestResumeRequest, request: Request, response: Response, db: Db) -> GuestOut:
    svc.require_enabled()
    user = await svc.find_guest(db, body.survey_code, _ip(request))
    return await _start(db, response, user, body.lesson_key)


@router.get("/admin/survey/export.csv", tags=["admin"], operation_id="exportSurveyCsv", summary="Survey data export (CSV)",
            description="One row per guest answer: `survey_code, lesson, item, first_attempt_is_correct, answered_at_utc, hints_used, max_hint_level, "
            "chat_asks, used_explain, blocked_count` (Habit counters, never message text). No other identifying column.",
            responses={200: {"content": {"text/csv": {"schema": {"type": "string"}}}, "description": "CSV file."},
                       **errs(401, 403)})
async def export_survey(cu: Annotated[CurrentUser, Depends(require_role("ADMIN", "TEACHER"))], db: Db) -> Response:
    body = await svc.export_csv(db)
    audit(db, cu.id, "EXPORT_SURVEY", "survey")
    await db.commit()
    return Response(body, media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="survey.csv"'})


@router.get("/admin/survey/stats", tags=["admin"], operation_id="getSurveyStats", response_model=SurveyStats,
            summary="Guest counters (ADMIN)", description="Active guests, guests created in the last hour and the limits.",
            responses=errs(401, 403))
async def survey_stats(cu: Annotated[CurrentUser, Depends(require_role("ADMIN"))], db: Db) -> SurveyStats:
    out = SurveyStats(**await svc.stats(db), **await habit_stats(db))
    audit(db, cu.id, "ADMIN_VIEW_SURVEY_STATS", "survey")
    await db.commit()
    return out
