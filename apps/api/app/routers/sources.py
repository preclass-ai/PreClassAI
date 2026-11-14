from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, UploadFile

from app.routers._base import errs, todo
from app.schemas import (
    AnchorList,
    SourceCreateText,
    SourceList,
    SourceOut,
    SourceRevisionCreateText,
    Visibility,
)

router = APIRouter(tags=["sources"])

_UPLOAD = ("Upload limits: DOCX only (`PK` magic + content types), ≤ 10 MB, macros rejected → 422. "
           "Parsing is synchronous: the response already has `extractStatus` and `anchorCount`.")


@router.post("/sources", status_code=201, operation_id="createSourceFromText", response_model=SourceOut,
             summary="Create a source from pasted text (TEACHER)",
             description="Creates the asset and revision 1; paragraphs (blank-line separated) become anchors.",
             responses=errs(401, 403, 422))
async def create_source_text(body: SourceCreateText) -> SourceOut:
    todo()


@router.post("/sources/docx", status_code=201, operation_id="createSourceFromDocx", response_model=SourceOut,
             summary="Create a source from a DOCX file (TEACHER, multipart)", description=_UPLOAD,
             responses=errs(401, 403, 422))
async def create_source_docx(
    file: Annotated[UploadFile, File()], title: Annotated[str, Form()],
    license_note: Annotated[str | None, Form(alias="licenseNote")] = None,
    visibility: Annotated[Visibility, Form()] = "PRIVATE",
) -> SourceOut:
    todo()


@router.get("/sources", operation_id="listSources", response_model=SourceList,
            summary="Own sources plus SCHOOL-visible ones", responses=errs(401, 403))
async def list_sources() -> SourceList:
    todo()


@router.get("/sources/{source_id}", operation_id="getSource", response_model=SourceOut, summary="One source",
            responses=errs(401, 404))
async def get_source(source_id: UUID) -> SourceOut:
    todo()


@router.post("/sources/{source_id}/revisions", status_code=201, operation_id="createSourceRevisionFromText",
             response_model=SourceOut, summary="New source revision from text (owner)",
             description="Creates revision N+1 with new hashes. Lessons are NOT changed automatically: they get "
             "`newerSourceAvailable=true`; attach it with PUT /revisions/{id}/sources.",
             responses=errs(401, 404, 422))
async def create_source_revision_text(source_id: UUID, body: SourceRevisionCreateText) -> SourceOut:
    todo()


@router.post("/sources/{source_id}/revisions/docx", status_code=201,
             operation_id="createSourceRevisionFromDocx", response_model=SourceOut,
             summary="New source revision from a DOCX file (owner, multipart)", description=_UPLOAD,
             responses=errs(401, 404, 422))
async def create_source_revision_docx(source_id: UUID, file: Annotated[UploadFile, File()]) -> SourceOut:
    todo()


@router.get("/source-revisions/{source_revision_id}/anchors", operation_id="listAnchors",
            response_model=AnchorList, summary="Anchors of a source revision (owner / SCHOOL)",
            responses=errs(401, 404))
async def list_anchors(source_revision_id: UUID) -> AnchorList:
    todo()
