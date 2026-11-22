from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app import habit as svc
from app.auth import CurrentUser, require_role
from app.db.session import get_db
from app.routers._base import errs
from app.schemas import ChatReply, ChatRequest, HabitOut

router = APIRouter(prefix="/student", tags=["habit"])
Student = Annotated[CurrentUser, Depends(require_role("STUDENT"))]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.get("/assignments/{assignment_id}/habit", operation_id="getHabit", response_model=HabitOut,
            summary="Study habit of the student for this assignment (streak, daily goal, badges, hints used)",
            description="404 when `CHAT_ENABLED` is off or the assignment is not the student's.",
            responses=errs(401, 403, 404, 410))
async def get_habit(assignment_id: UUID, cu: Student, db: Db) -> HabitOut:
    return await svc.habit(db, cu, assignment_id)


@router.post("/assignments/{assignment_id}/chat", operation_id="chatHabit", response_model=ChatReply,
             summary="Ask Habit for a hint (1→3), a scoped answer from the approved lesson, or an explanation after answering",
             description="Grounded only in the published snapshot. Before the student answers the item the reply never "
             "contains the answer (label, value, or a verdict on one option); asks for it are refused with a "
             "`blockedReason`. `explain` needs the student's own attempt. Limits: `CHAT_MAX_MSGS_PER_ITEM`, "
             "`CHAT_MAX_MSGS_PER_DAY` (typed questions) and `HINT_MAX_PER_ITEM` (hint presses). Repeating the same `requestId` returns the stored reply.",
             responses=errs(401, 403, 404, 410, 422,
                            (409, "NOT_ANSWERED (explain trước khi trả lời) hoặc ALREADY_ANSWERED (xin gợi ý sau khi nộp)."),
                            (429, "CHAT_LIMIT hoặc HINT_LIMIT.")))
async def chat(assignment_id: UUID, body: ChatRequest, cu: Student, db: Db) -> ChatReply:
    return await svc.chat(db, cu, assignment_id, body)
