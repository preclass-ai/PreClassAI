from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import insights as svc
from app.auth import CurrentUser, require_role
from app.db.session import get_db
from app.routers._base import errs
from app.schemas import AnalyzeOut, InsightsOut, ReteachOut

router = APIRouter(prefix="/classes/{class_id}/assignments/{assignment_id}/insights", tags=["insights"])
Teacher = Annotated[CurrentUser, Depends(require_role("TEACHER"))]
Db = Annotated[AsyncSession, Depends(get_db)]
_NOTE = "Only a TEACHER of the class; anything else is 404. Anonymous: no student id, name or survey code in the answer."


@router.get("", operation_id="getAssignmentInsights", response_model=InsightsOut,
            summary="What students ask HABIT AI and where they struggle (class teacher)",
            description=_NOTE + " Questions are grouped by rules (0đ) into themes; items carry first-attempt rate and hint use.",
            responses=errs(401, 403, 404))
async def get_insights(class_id: UUID, assignment_id: UUID, cu: Teacher, db: Db) -> InsightsOut:
    return await svc.insights(db, cu, class_id, assignment_id)


@router.post("/analyze", operation_id="analyzeAssignmentInsights", response_model=AnalyzeOut,
             summary="3 to 5 topics students get stuck on (rules, or one model call when CHAT_MODE=llm)",
             description=_NOTE + " Pressed by the teacher only. The model call is cached for 10 minutes and counts against "
             "`CHAT_DAILY_TOKEN_BUDGET`; any failure falls back to the rule topics.",
             responses=errs(401, 403, 404))
async def analyze(class_id: UUID, assignment_id: UUID, cu: Teacher, db: Db) -> AnalyzeOut:
    return await svc.analyze(db, cu, class_id, assignment_id)


@router.post("/reteach", status_code=201, operation_id="createReteachDraft", response_model=ReteachOut,
             summary="Draft blocks to re-teach the items most students missed (lesson author only)",
             description=_NOTE + " Quotes up to 3 approved source passages behind the flagged items into a DRAFT revision "
             "(a new one when the current revision is published). VAL-01..10 run; nothing is approved or published. "
             "409 `NOTHING_TO_RETEACH` when no item is flagged.",
             responses=errs(401, 403, 404, (409, "NOTHING_TO_RETEACH, DRAFT_EXISTS")))
async def reteach(class_id: UUID, assignment_id: UUID, cu: Teacher, db: Db) -> ReteachOut:
    return await svc.reteach(db, cu, class_id, assignment_id)


