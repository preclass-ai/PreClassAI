from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser, require_role
from app.db.session import get_db
from app.errors import ApiError
from app.routers._base import errs
from app.schemas import (
    AnchorList,
    SourceCreateText,
    SourceList,
    SourceOut,
    SourceRevisionCreateText,
    Visibility,
)
from app.sources import service
from app.sources.parse import MAX_UPLOAD_BYTES

router = APIRouter(tags=["sources"])

Db = Annotated[AsyncSession, Depends(get_db)]
Teacher = Annotated[CurrentUser, Depends(require_role("TEACHER"))]
Reader = Annotated[CurrentUser, Depends(require_role("TEACHER", "REVIEWER"))]

_UPLOAD = ("Upload limits: DOCX only (`PK` magic + content types), ≤ 10 MB, macros rejected → 422 "
           "(`INVALID_FILE`, `FILE_TOO_LARGE`, `MACRO_REJECTED`, `EMPTY_SOURCE`). The client's file name is ignored. "
           "Parsing is synchronous: the response already has `extractStatus` and `anchorCount`.")


async def _read_upload(file: UploadFile) -> bytes:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", "Tệp vượt quá 10 MB")
    return data


@router.post("/sources", status_code=201, operation_id="createSourceFromText", response_model=SourceOut,
             summary="Create a source from pasted text (TEACHER)",
             description="Creates the asset and revision 1; paragraphs (blank-line separated) become anchors, the "
             "first one is the heading. `visibility=SCHOOL` requires `licenseNote` (422 `LICENSE_REQUIRED`).",
             responses=errs(401, 403, 422))
async def create_source_text(body: SourceCreateText, cu: Teacher, db: Db) -> SourceOut:
    return await service.create_source(db, cu, body.title, body.license_note, body.visibility, text=body.text)


@router.post("/sources/docx", status_code=201, operation_id="createSourceFromDocx", response_model=SourceOut,
             summary="Create a source from a DOCX file (TEACHER, multipart)", description=_UPLOAD,
             responses=errs(401, 403, 422))
async def create_source_docx(
    cu: Teacher, db: Db, file: Annotated[UploadFile, File()], title: Annotated[str, Form()],
    license_note: Annotated[str | None, Form(alias="licenseNote")] = None,
    visibility: Annotated[Visibility, Form()] = "PRIVATE",
) -> SourceOut:
    return await service.create_source(db, cu, title, license_note, visibility, docx=await _read_upload(file))


_FILE = ("Accepts DOCX, PDF, XLSX, PPTX; the type is read from the file's magic bytes, the client's name and Content-Type are "
         "ignored. Limits: 10 MB; ≤ 1000 zip entries, ≤ 20 MB unzipped; ≤ 50 PDF pages, ≤ 5 sheets × 2000 cells, ≤ 60 slides "
         "(env `SOURCE_*`). Rejected with 422: `FILE_TOO_LARGE`, `SOURCE_TOO_LARGE`, `INVALID_FILE`, `MACRO_REJECTED`, "
         "`EXTERNAL_CONTENT_REJECTED`, `ACTIVE_CONTENT_REJECTED` (PDF JavaScript/attachments), `PARSE_TIMEOUT` (30 s), "
         "`EMPTY_SOURCE`. A PDF without a text layer returns 201 with `extractStatus=FAILED`, `extractError=SCANNED_PDF` (no OCR). "
         "Anchor locators: PDF `{page, para}`, XLSX `{sheet, row, col, header?}` (0-based row/col, stored values only, formulas "
         "are never evaluated), PPTX `{slide, shape, para}` or `{slide, shape, row, col}`.")


@router.post("/sources/file", status_code=201, operation_id="createSourceFromFile", response_model=SourceOut,
             summary="Create a source from a DOCX, PDF, XLSX or PPTX file (TEACHER, multipart)", description=_FILE,
             responses=errs(401, 403, 422))
async def create_source_file(
    cu: Teacher, db: Db, file: Annotated[UploadFile, File()], title: Annotated[str, Form()],
    license_note: Annotated[str | None, Form(alias="licenseNote")] = None,
    visibility: Annotated[Visibility, Form()] = "PRIVATE",
) -> SourceOut:
    return await service.create_file_source(db, cu, title, license_note, visibility, await _read_upload(file))


@router.get("/sources", operation_id="listSources", response_model=SourceList,
            summary="Own sources plus SCHOOL-visible ones", responses=errs(401, 403))
async def list_sources(cu: Reader, db: Db) -> SourceList:
    return await service.list_sources(db, cu)


@router.get("/sources/{source_id}", operation_id="getSource", response_model=SourceOut, summary="One source",
            responses=errs(401, 403, 404))
async def get_source(source_id: UUID, cu: Reader, db: Db) -> SourceOut:
    return await service.get_source(db, cu, source_id)


@router.post("/sources/{source_id}/revisions", status_code=201, operation_id="createSourceRevisionFromText",
             response_model=SourceOut, summary="New source revision from text (owner)",
             description="Creates revision N+1 with new hashes (identical content → 409 `SOURCE_UNCHANGED`). Lessons "
             "are NOT changed automatically: they get `newerSourceAvailable=true`; attach it with "
             "PUT /revisions/{id}/sources.",
             responses=errs(401, 403, 404, 422, (409, "SOURCE_UNCHANGED.")))
async def create_source_revision_text(
    source_id: UUID, body: SourceRevisionCreateText, cu: Teacher, db: Db
) -> SourceOut:
    return await service.add_revision(db, cu, source_id, text=body.text)


@router.post("/sources/{source_id}/revisions/docx", status_code=201,
             operation_id="createSourceRevisionFromDocx", response_model=SourceOut,
             summary="New source revision from a DOCX file (owner, multipart)", description=_UPLOAD,
             responses=errs(401, 403, 404, 422, (409, "SOURCE_UNCHANGED.")))
async def create_source_revision_docx(
    source_id: UUID, cu: Teacher, db: Db, file: Annotated[UploadFile, File()]
) -> SourceOut:
    return await service.add_revision(db, cu, source_id, docx=await _read_upload(file))


@router.get("/source-revisions/{source_revision_id}/anchors", operation_id="listAnchors",
            response_model=AnchorList, summary="Anchors of a source revision (owner / SCHOOL)",
            responses=errs(401, 403, 404))
async def list_anchors(source_revision_id: UUID, cu: Reader, db: Db) -> AnchorList:
    return await service.list_anchors(db, cu, source_revision_id)
