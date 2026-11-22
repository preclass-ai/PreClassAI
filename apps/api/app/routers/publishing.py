from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app import publish as svc
from app.auth import CurrentUser, require_role
from app.db.session import get_db
from app.routers._base import errs
from app.schemas import (
    ApproveAllOut,
    ApproveAllRequest,
    AssignmentCreate,
    AssignmentList,
    AssignmentOut,
    PublishCheckOut,
    PublishedOut,
    PublishRequest,
    ReviewOut,
    ReviewQueue,
    ReviewRequest,
    ReviewStatus,
    RevisionOut,
    WithdrawRequest,
)

router = APIRouter()


@router.get("/revisions/{revision_id}/review-queue", tags=["review"], operation_id="getReviewQueue",
            response_model=ReviewQueue, summary="Blocks needing review, FLAGGED first (screen S04)",
            responses=errs(401, 404))
async def review_queue(
    revision_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER", "REVIEWER"))], db: Annotated[AsyncSession, Depends(get_db)],
    status: list[ReviewStatus] = Query(["FLAGGED", "REVIEW_AGAIN", "UNREVIEWED"]),  # noqa: B008
) -> ReviewQueue:
    return await svc.review_queue(db, cu, revision_id, list(status))


@router.post("/blocks/{block_id}/reviews", tags=["review"], status_code=201, operation_id="reviewBlock",
             response_model=ReviewOut, summary="Approve / reject / request changes on one block (author or reviewer)",
             description="One block per call (bulk approve exists only for blocks without warnings: approve-all). `contentHash` must equal the "
             "current block hash.",
             responses=errs(401, 403, 404, (409, "STALE_REVIEW (hash cũ) hoặc REVISION_LOCKED.")))
async def review_block(block_id: UUID, body: ReviewRequest, cu: Annotated[CurrentUser, Depends(require_role("TEACHER", "REVIEWER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> ReviewOut:
    return await svc.review_block(db, cu, block_id, body)


@router.post("/revisions/{revision_id}/approve-all", tags=["review"], operation_id="approveAllClean", response_model=ApproveAllOut,
             summary="Approve every 'machine-checked' block that has no warning (author)",
             description="Only AUTO_CHECKED blocks with no failed rule. Blocks with a warning, a blocker or a stale check stay for a "
             "hand review. `confirm=false` only counts (nothing written); `confirm=true` writes one review event per block.",
             responses=errs(401, 404, (409, "REVISION_LOCKED.")))
async def approve_all(revision_id: UUID, body: ApproveAllRequest, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> ApproveAllOut:
    return await svc.approve_all(db, cu, revision_id, body.confirm)


@router.get("/revisions/{revision_id}/publish-check", tags=["publish"], operation_id="getPublishCheck",
            response_model=PublishCheckOut, summary="Publish gate checklist, read-only (screen S05)",
            responses=errs(401, 404))
async def publish_check(revision_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> PublishCheckOut:
    return await svc.publish_check(db, cu, revision_id)


@router.post("/revisions/{revision_id}/publish", tags=["publish"], status_code=201, operation_id="publishRevision",
             response_model=PublishedOut, summary="Publish an immutable snapshot (author)",
             responses=errs(401, 404, 422, (409, "PUBLISH_BLOCKED (kèm blockIds), VERSION_CONFLICT, REVISION_LOCKED.")))
async def publish(revision_id: UUID, body: PublishRequest, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> PublishedOut:
    return await svc.publish(db, cu, revision_id, body.confirm_checked, body.version)


@router.post("/revisions/{revision_id}/new-revision", tags=["publish"], status_code=201,
             operation_id="createNewRevision", response_model=RevisionOut,
             summary="Copy a published revision into a new DRAFT (author)",
             description="Approvals are not carried over; the published snapshot stays untouched.",
             responses=errs(401, 404, (409, "NOT_PUBLISHED, DRAFT_EXISTS.")))
async def new_revision(revision_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> RevisionOut:
    return await svc.new_revision(db, cu, revision_id)


@router.post("/published/{published_id}/withdraw", tags=["publish"], operation_id="withdrawPublished",
             response_model=PublishedOut, summary="Withdraw a published version (author)",
             description="Students then get 410 `WITHDRAWN`. The reason is logged.", responses=errs(401, 404, 422))
async def withdraw(published_id: UUID, body: WithdrawRequest, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> PublishedOut:
    return await svc.withdraw(db, cu, published_id, body.reason)


@router.get("/lessons/{lesson_id}/assignments", tags=["publish"], operation_id="listLessonAssignments",
            response_model=AssignmentList, summary="Classes this lesson is assigned to (author)",
            responses=errs(401, 403))
async def list_lesson_assignments(lesson_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> AssignmentList:
    return await svc.list_lesson_assignments(db, cu, lesson_id)


@router.post("/published/{published_id}/assignments", tags=["publish"], status_code=201,
             operation_id="createAssignment", response_model=AssignmentOut,
             summary="Assign a published version to a class (author)",
             responses=errs(401, 404, 422, (409, "WITHDRAWN: bản đã thu hồi.")))
async def create_assignment(published_id: UUID, body: AssignmentCreate, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> AssignmentOut:
    return await svc.create_assignment(db, cu, published_id, body)
