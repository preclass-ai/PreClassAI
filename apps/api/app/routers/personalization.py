from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import personalization as svc
from app.auth import CurrentUser, require_role
from app.db.session import get_db
from app.routers._base import errs
from app.schemas import PreferencesIn, PreferencesOut

router = APIRouter(prefix="/student", tags=["personalization"])
Student = Annotated[CurrentUser, Depends(require_role("STUDENT"))]
Db = Annotated[AsyncSession, Depends(get_db)]
_NOTE = ("404 when `PERSONALIZATION_ENABLED` is off. Only options the student chose; never a label about the student "
         "(ADR-0013). A missing key means the option is off.")


@router.get("/preferences", operation_id="getPreferences", response_model=PreferencesOut,
            summary="The student's own learning options", description=_NOTE, responses=errs(401, 403, 404))
async def get_preferences(cu: Student, db: Db) -> PreferencesOut:
    return await svc.read_prefs(db, cu)


@router.put("/preferences", operation_id="updatePreferences", response_model=PreferencesOut,
            summary="Switch learning options on or off (partial update)", description=_NOTE,
            responses=errs(401, 403, 404, 422))
async def update_preferences(body: PreferencesIn, cu: Student, db: Db) -> PreferencesOut:
    return await svc.put_prefs(db, cu, body)


@router.delete("/preferences", operation_id="resetPreferences", response_model=PreferencesOut,
               summary="Switch every option off", description=_NOTE, responses=errs(401, 403, 404))
async def reset_preferences(cu: Student, db: Db) -> PreferencesOut:
    return await svc.reset_prefs(db, cu)
