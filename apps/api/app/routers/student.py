from uuid import UUID

from fastapi import APIRouter

from app.routers._base import errs, todo
from app.schemas import AttemptRequest, AttemptResult, StudentAssignmentList, StudentAssignmentOut

router = APIRouter(prefix="/student", tags=["student"])


@router.get("/assignments", operation_id="listStudentAssignments", response_model=StudentAssignmentList,
            summary="Open assignments of the student's classes (STUDENT)", responses=errs(401, 403))
async def list_assignments() -> StudentAssignmentList:
    todo()


@router.get("/assignments/{assignment_id}", operation_id="getStudentAssignment",
            response_model=StudentAssignmentOut,
            summary="Assignment content from the published snapshot (screen S07)",
            description="Whitelist DTO: no provenance, review, validation, answer key or explanation before the "
            "student answers an item. Before `openAt` → 404. Withdrawn → 410.",
            responses=errs(401, 403, 404, 410))
async def get_assignment(assignment_id: UUID) -> StudentAssignmentOut:
    todo()


@router.post("/assignments/{assignment_id}/attempts", status_code=201, operation_id="submitAttempt",
             response_model=AttemptResult,
             summary="Answer one item; the result and explanation come back now",
             description="One attempt per item. Repeating the same `requestId` returns the stored result.",
             responses=errs(401, 403, 404, 410, 422,
                            (409, "ASSIGNMENT_CLOSED (sau hạn) hoặc ALREADY_ANSWERED (câu này đã trả lời).")))
async def submit_attempt(assignment_id: UUID, body: AttemptRequest) -> AttemptResult:
    todo()
