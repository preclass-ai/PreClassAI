from uuid import UUID

from fastapi import APIRouter, Query

from app.routers._base import errs, todo
from app.schemas import (
    AssignmentCreate,
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
    revision_id: UUID,
    status: list[ReviewStatus] = Query(["FLAGGED", "REVIEW_AGAIN", "UNREVIEWED"]),  # noqa: B008
) -> ReviewQueue:
    todo()


@router.post("/blocks/{block_id}/reviews", tags=["review"], status_code=201, operation_id="reviewBlock",
             response_model=ReviewOut, summary="Approve / reject / request changes on one block (author or reviewer)",
             description="One block per call; there is no bulk approve (PR-02). `contentHash` must equal the "
             "current block hash.",
             responses=errs(401, 403, 404, (409, "STALE_REVIEW (hash cũ) hoặc REVISION_LOCKED.")))
async def review_block(block_id: UUID, body: ReviewRequest) -> ReviewOut:
    todo()


@router.get("/revisions/{revision_id}/publish-check", tags=["publish"], operation_id="getPublishCheck",
            response_model=PublishCheckOut, summary="Publish gate checklist, read-only (screen S05)",
            responses=errs(401, 404))
async def publish_check(revision_id: UUID) -> PublishCheckOut:
    todo()


@router.post("/revisions/{revision_id}/publish", tags=["publish"], status_code=201, operation_id="publishRevision",
             response_model=PublishedOut, summary="Publish an immutable snapshot (author)",
             responses=errs(401, 404, 422, (409, "PUBLISH_BLOCKED (kèm blockIds), VERSION_CONFLICT, REVISION_LOCKED.")))
async def publish(revision_id: UUID, body: PublishRequest) -> PublishedOut:
    todo()


@router.post("/revisions/{revision_id}/new-revision", tags=["publish"], status_code=201,
             operation_id="createNewRevision", response_model=RevisionOut,
             summary="Copy a published revision into a new DRAFT (author)",
             description="Approvals are not carried over; the published snapshot stays untouched.",
             responses=errs(401, 404, (409, "NOT_PUBLISHED, DRAFT_EXISTS.")))
async def new_revision(revision_id: UUID) -> RevisionOut:
    todo()


@router.post("/published/{published_id}/withdraw", tags=["publish"], operation_id="withdrawPublished",
             response_model=PublishedOut, summary="Withdraw a published version (author)",
             description="Students then get 410 `WITHDRAWN`. The reason is logged.", responses=errs(401, 404, 422))
async def withdraw(published_id: UUID, body: WithdrawRequest) -> PublishedOut:
    todo()


@router.post("/published/{published_id}/assignments", tags=["publish"], status_code=201,
             operation_id="createAssignment", response_model=AssignmentOut,
             summary="Assign a published version to a class (author)",
             responses=errs(401, 404, 422, (409, "WITHDRAWN: bản đã thu hồi.")))
async def create_assignment(published_id: UUID, body: AssignmentCreate) -> AssignmentOut:
    todo()
