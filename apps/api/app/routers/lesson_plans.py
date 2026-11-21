from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, require_role
from app.db.session import get_db
from app.lessonplan import service
from app.lessonplan.service import PlanRunner, plan_runner
from app.routers._base import errs
from app.routers.sources import _read_upload
from app.schemas import (
    CompetencyList,
    McqCompetency,
    PlanDetail,
    PlanJobLatest,
    PlanJobOut,
    PlanLessonOut,
    PlanList,
    PlanMcqAnswer,
)

router = APIRouter(prefix="/lesson-plans", tags=["lesson-plans"])
Teacher = Annotated[CurrentUser, Depends(require_role("TEACHER"))]
Db = Annotated[AsyncSession, Depends(get_db)]


@router.post("", status_code=202, operation_id="uploadLessonPlan", response_model=PlanJobOut,
             summary="Start reading a lesson plan in the background (DOCX or PDF with a text layer; TEACHER, multipart)",
             description="Returns 202 with a job at once; poll `GET /lesson-plans/jobs/{id}` (queued, parsing with page x/y, done with "
             "`planIds`, or failed with a friendly message). One active job per teacher (409 `PARSE_BUSY`). One file can hold several "
             "lessons: one plan per lesson. Signature blocks and teacher names are removed; an MCQ answer comes from an underline or "
             "from the teacher, never from a model. Quick 422: `UNSUPPORTED_FILE`, `FILE_TOO_LARGE`, `INVALID_FILE`. Reading errors "
             "(`SCANNED_PDF`, `PARSE_TIMEOUT` 120 s, `EMPTY_SOURCE`) arrive in the job.",
             responses=errs(401, 403, (409, "PARSE_BUSY"), 422))
async def upload(cu: Teacher, db: Db, runner: Annotated[PlanRunner, Depends(plan_runner)],
                 file: Annotated[UploadFile, File()]) -> PlanJobOut:
    return await service.start_upload(db, cu, await _read_upload(file), file.filename, runner)


@router.get("/competencies", operation_id="listCompetencies", response_model=CompetencyList,
            summary="Competency catalogue per subject (TEACHER)", responses=errs(401, 403))
async def competencies(cu: Teacher, db: Db) -> CompetencyList:
    return await service.competencies(db)


@router.get("/jobs/latest", operation_id="getLatestPlanJob", response_model=PlanJobLatest,
            summary="My most recent reading job, so the page can resume after a reload (TEACHER)", responses=errs(401, 403))
async def latest_job(cu: Teacher, db: Db) -> PlanJobLatest:
    return await service.latest_job(db, cu)


@router.get("/jobs/{job_id}", operation_id="getPlanJob", response_model=PlanJobOut,
            summary="State of a reading job (owner only)", responses=errs(401, 403, 404))
async def get_job(job_id: UUID, cu: Teacher, db: Db) -> PlanJobOut:
    return await service.get_job(db, cu, job_id)


@router.get("", operation_id="listLessonPlans", response_model=PlanList, summary="My lesson plans (TEACHER)",
            responses=errs(401, 403))
async def list_plans(cu: Teacher, db: Db) -> PlanList:
    return await service.list_plans(db, cu)


@router.get("/{plan_id}", operation_id="getLessonPlan", response_model=PlanDetail,
            summary="What was read from one lesson plan (owner only)", responses=errs(401, 403, 404))
async def get_plan(plan_id: UUID, cu: Teacher, db: Db) -> PlanDetail:
    return await service.get_plan(db, cu, plan_id)


@router.put("/{plan_id}/mcqs/{mcq_id}/answer", operation_id="confirmPlanMcqAnswer", response_model=PlanDetail,
            summary="The teacher confirms the correct option of an MCQ (answer source = teacher)",
            responses=errs(401, 403, 404, 422))
async def confirm(plan_id: UUID, mcq_id: UUID, body: PlanMcqAnswer, cu: Teacher, db: Db) -> PlanDetail:
    return await service.set_answer(db, cu, plan_id, mcq_id, body.correct_option)


@router.put("/{plan_id}/mcqs/{mcq_id}/competency", operation_id="setPlanMcqCompetency", response_model=PlanDetail,
            summary="The teacher sets the competency of an MCQ (code from the subject catalogue, or null)",
            responses=errs(401, 403, 404, 422))
async def set_competency(plan_id: UUID, mcq_id: UUID, body: McqCompetency, cu: Teacher, db: Db) -> PlanDetail:
    return await service.set_mcq_competency(db, cu, plan_id, mcq_id, body.competency_code)


@router.post("/{plan_id}/lesson", status_code=201, operation_id="createLessonFromPlan", response_model=PlanLessonOut,
             summary="Create the pre-class lesson draft (DRAFT blocks, validated, never approved or published)",
             description="Mapping: opening -> 1 trigger question; knowledge boxes -> up to 2 reading cards and 1 flashcard quoted "
             "verbatim; up to 5 teacher-confirmed MCQ with a templated explanation; application -> 1 after-class task. MCQ without "
             "a confirmed answer are skipped (`skippedUnconfirmed`). 409 `LESSON_EXISTS` when it was already created. Review and "
             "publish with the usual lesson workspace.",
             responses=errs(401, 403, (409, "LESSON_EXISTS"), 404))
async def create_lesson(plan_id: UUID, cu: Teacher, db: Db) -> PlanLessonOut:
    return await service.build_lesson(db, cu, plan_id)
