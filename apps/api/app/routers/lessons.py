from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app import blocks as blocks_service
from app import lessons as lessons_service
from app.auth import CurrentUser, require_role
from app.db.session import get_db
from app.lessons import replace_sources as replace_sources_service
from app.routers._base import errs, todo
from app.schemas import (
    BlockCreate,
    BlockList,
    BlockOut,
    BlockPatch,
    GenerateRequest,
    JobAccepted,
    JobOut,
    LessonCreate,
    LessonHistory,
    LessonList,
    LessonOut,
    ProvenanceOut,
    ProvenanceUpdate,
    RevisionSourcesResult,
    RevisionSourcesUpdate,
    ValidateOut,
)

router = APIRouter()
_LOCKED = (409, "VERSION_CONFLICT (version cũ) hoặc REVISION_LOCKED (bản đã xuất bản không sửa được).")


@router.post("/lessons", tags=["lessons"], status_code=201, operation_id="createLesson", response_model=LessonOut,
             summary="Create a lesson with its first DRAFT revision (TEACHER)", responses=errs(401, 403, 404, 422))
async def create_lesson(body: LessonCreate, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> LessonOut:
    return await lessons_service.create_lesson(db, cu, body)


@router.get("/lessons", tags=["lessons"], operation_id="listLessons", response_model=LessonList,
            summary="Own lessons (TEACHER) or assigned ones (REVIEWER)", responses=errs(401, 403))
async def list_lessons(cu: Annotated[CurrentUser, Depends(require_role("TEACHER", "REVIEWER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> LessonList:
    return await lessons_service.list_lessons(db, cu)


@router.get("/lessons/{lesson_id}", tags=["lessons"], operation_id="getLesson", response_model=LessonOut,
            summary="One lesson with its current revision", responses=errs(401, 404))
async def get_lesson(lesson_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER", "REVIEWER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> LessonOut:
    return await lessons_service.get_lesson(db, cu, lesson_id)


@router.get("/lessons/{lesson_id}/history", tags=["lessons"], operation_id="getLessonHistory",
            response_model=LessonHistory, summary="Revisions, summary diff and events (screen S06)",
            responses=errs(401, 404))
async def lesson_history(lesson_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER", "REVIEWER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> LessonHistory:
    return await lessons_service.lesson_history(db, cu, lesson_id)


@router.post("/lessons/{lesson_id}/generate", tags=["generation"], status_code=202, operation_id="generateDraft",
             response_model=JobAccepted, summary="Start AI draft generation (author)",
             description="Only the teacher's explicit action triggers AI (PR-09). Poll GET /jobs/{id}.",
             responses=errs(401, 404, 422, (409, "JOB_ALREADY_RUNNING, REVISION_NOT_EMPTY (use mode=append)."),
                            503))
async def generate(lesson_id: UUID, body: GenerateRequest) -> JobAccepted:
    todo()


@router.get("/jobs/{job_id}", tags=["generation"], operation_id="getJob", response_model=JobOut,
            summary="Generation job status (author)", responses=errs(401, 404))
async def get_job(job_id: UUID) -> JobOut:
    todo()


@router.put("/revisions/{revision_id}/sources", tags=["lessons"], operation_id="replaceRevisionSources",
            response_model=RevisionSourcesResult, summary="Attach other source revisions (DRAFT only, author)",
            description="One transaction: every block linked to an anchor of a removed source revision, the blocks "
            "depending on it and its parents go to REVIEW_AGAIN (SOURCE_REPLACED event). Links are re-pointed by "
            "identical excerptHash (VERIFIED), otherwise UNRESOLVED. Published lessons are never affected.",
            responses=errs(401, 404, 422, _LOCKED))
async def replace_sources(
    revision_id: UUID,
    body: RevisionSourcesUpdate,
    cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> RevisionSourcesResult:
    return await replace_sources_service(db, cu, revision_id, body)


@router.get("/revisions/{revision_id}/blocks", tags=["blocks"], operation_id="listBlocks", response_model=BlockList,
            summary="All blocks of a revision, flat, ordered by position (author / assigned reviewer)",
            responses=errs(401, 404))
async def list_blocks(revision_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER", "REVIEWER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> BlockList:
    return await blocks_service.list_blocks(db, cu, revision_id)


@router.post("/revisions/{revision_id}/blocks", tags=["blocks"], status_code=201, operation_id="createBlock",
             response_model=BlockOut, summary="Add a TEACHER_AUTHORED block (author)",
             responses=errs(401, 404, 422, _LOCKED))
async def create_block(revision_id: UUID, body: BlockCreate, request: Request, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> BlockOut:
    raw = (await request.json()).get("payload")  # exact payload: the schema union may drop unknown keys
    return await blocks_service.create_block(db, cu, revision_id, body, raw)


@router.patch("/blocks/{block_id}", tags=["blocks"], operation_id="patchBlock", response_model=BlockOut,
              summary="Edit a block (author)",
              description="Writes a transformation event, recomputes the hash, sets the block and its dependents "
              "(and direct parent) to REVIEW_AGAIN if they were APPROVED, and re-runs validation.",
              responses=errs(401, 404, 422, _LOCKED))
async def patch_block(block_id: UUID, body: BlockPatch, request: Request, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> BlockOut:
    raw = (await request.json()).get("payload")
    return await blocks_service.patch_block(db, cu, block_id, raw, body.version)


@router.delete("/blocks/{block_id}", tags=["blocks"], status_code=204, operation_id="deleteBlock",
               summary="Soft-delete a block (author, unpublished revisions only)",
               responses=errs(401, 404, _LOCKED))
async def delete_block(block_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> None:
    await blocks_service.delete_block(db, cu, block_id)


@router.get("/blocks/{block_id}/provenance", tags=["provenance"], operation_id="getProvenance",
            response_model=ProvenanceOut, summary="Source Inspector data for a block (author / reviewer)",
            description="Writes an `INSPECT_PROVENANCE` audit entry (no content). Students get 404.",
            responses=errs(401, 404))
async def get_provenance(block_id: UUID, cu: Annotated[CurrentUser, Depends(require_role("TEACHER", "REVIEWER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> ProvenanceOut:
    return await blocks_service.get_provenance(db, cu, block_id)


@router.put("/blocks/{block_id}/provenance", tags=["provenance"], operation_id="putProvenance",
            response_model=ProvenanceOut, summary="Set links or a no-source reason (author)",
            description="Send `links` or `noSourceReason`. The server verifies each anchor belongs to the "
            "lesson's sources; it never trusts anchor ids from the LLM.",
            responses=errs(401, 404, 422, _LOCKED))
async def put_provenance(block_id: UUID, body: ProvenanceUpdate, cu: Annotated[CurrentUser, Depends(require_role("TEACHER"))], db: Annotated[AsyncSession, Depends(get_db)]) -> ProvenanceOut:
    return await blocks_service.put_provenance(db, cu, block_id, body)


@router.post("/revisions/{revision_id}/validate", tags=["validation"], operation_id="validateRevision",
             response_model=ValidateOut, summary="Run all validation rules (author)", responses=errs(401, 404))
async def validate(revision_id: UUID) -> ValidateOut:
    todo()
