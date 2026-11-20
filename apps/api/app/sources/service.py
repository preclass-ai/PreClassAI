"""Source library services. Owner sees own sources; SCHOOL sources are visible to teachers/reviewers.

Anything not visible answers 404 (never 403) so ids cannot be probed.
"""

import hashlib
import uuid
from pathlib import Path
from uuid import UUID

from sqlalchemy import func, insert, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentUser
from app.config import get_settings
from app.db import models as m
from app.errors import ApiError
from app.hashing import sha256_hex
from app.schemas import AnchorList, AnchorOut, SourceList, SourceOut, SourceRevisionOut
from app.sources.formats import MIME, Limits, detect_kind, parse_isolated
from app.sources.parse import DOCX_MAIN, MAX_UPLOAD_BYTES, ParsedAnchor, parse_docx, parse_text

NOT_FOUND = ApiError(404, "NOT_FOUND", "Không tìm thấy")


def _visible(user: CurrentUser):  # type: ignore[no-untyped-def]
    return or_(m.SourceAsset.owner_id == user.id, m.SourceAsset.visibility == "SCHOOL")


async def _rev_out(db: AsyncSession, rev: m.SourceRevision) -> SourceRevisionOut:
    n = await db.scalar(select(func.count()).select_from(m.SourceAnchor).where(
        m.SourceAnchor.source_revision_id == rev.id))
    return SourceRevisionOut(id=rev.id, asset_id=rev.asset_id, version=rev.version, sha256=rev.sha256, mime=rev.mime,
                             extract_status=rev.extract_status,
                             extract_error="SCANNED_PDF" if rev.extract_status == "FAILED" else None,  # the only stored failure
                             anchor_count=n or 0, created_at=rev.created_at)


async def source_out(db: AsyncSession, asset: m.SourceAsset) -> SourceOut:
    latest = await db.scalar(select(m.SourceRevision).where(m.SourceRevision.asset_id == asset.id)
                             .order_by(m.SourceRevision.version.desc()).limit(1))
    if latest is None:
        raise NOT_FOUND
    return SourceOut(id=asset.id, title=asset.title, license_note=asset.license_note,
                     visibility=asset.visibility, owner_id=asset.owner_id,
                     latest_revision=await _rev_out(db, latest), created_at=asset.created_at)


async def _insert_revision(
    db: AsyncSession, asset_id: UUID, version: int, sha: str, mime: str, file_uri: str | None,
    anchors: list[ParsedAnchor], extract_status: str = "OK",
) -> m.SourceRevision:
    rev_id = uuid.uuid4()
    await db.execute(insert(m.SourceRevision), [{
        "id": rev_id, "asset_id": asset_id, "version": version, "sha256": sha, "mime": mime,
        "file_uri": file_uri, "extract_status": extract_status}])
    if anchors:
        await db.execute(insert(m.SourceAnchor), [{
        "id": uuid.uuid4(), "source_revision_id": rev_id, "code": f"anc_{str(rev_id)[:8]}_{i:03d}", "kind": a.kind,
        "locator": a.locator, "excerpt": a.excerpt, "excerpt_hash": a.hash, "numbers": a.numbers}
            for i, a in enumerate(anchors, start=1)])
    rev = await db.get(m.SourceRevision, rev_id)
    if rev is None:
        raise NOT_FOUND
    return rev


def _store_docx(data: bytes, ext: str = "docx") -> str:
    """Stored under a random name; the client's file name is never used as a path."""
    root = Path(get_settings().upload_dir)
    root.mkdir(parents=True, exist_ok=True)
    name = f"{uuid.uuid4()}.{ext}"
    (root / name).write_bytes(data)
    return name


def _material(text: str | None, docx: bytes | None) -> tuple[str, str, str | None, list[ParsedAnchor]]:
    """-> (sha256, mime, stored file name or None, anchors)"""
    if docx is not None:
        anchors = parse_docx(docx)  # validates the container first
        return sha256_hex_bytes(docx), DOCX_MAIN, _store_docx(docx), anchors
    if text is None:
        raise ApiError(422, "EMPTY_SOURCE", "Thiếu nội dung")
    return sha256_hex(text), "text/plain", None, parse_text(text)


def sha256_hex_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


async def create_source(
    db: AsyncSession, user: CurrentUser, title: str, license_note: str | None, visibility: str,
    text: str | None = None, docx: bytes | None = None,
) -> SourceOut:
    if visibility == "SCHOOL" and not (license_note or "").strip():  # VAL-09
        raise ApiError(422, "LICENSE_REQUIRED", "Nguồn chia sẻ toàn trường cần ghi chú bản quyền")
    sha, mime, uri, anchors = _material(text, docx)
    asset = m.SourceAsset(owner_id=user.id, title=title.strip(), license_note=license_note, visibility=visibility)
    db.add(asset)
    await db.flush()
    await _insert_revision(db, asset.id, 1, sha, mime, uri, anchors)
    await db.commit()
    return await source_out(db, asset)


async def add_revision(
    db: AsyncSession, user: CurrentUser, source_id: UUID, text: str | None = None, docx: bytes | None = None
) -> SourceOut:
    asset = await db.scalar(select(m.SourceAsset).where(m.SourceAsset.id == source_id,
                                                        m.SourceAsset.owner_id == user.id).with_for_update())
    if asset is None:
        raise NOT_FOUND
    latest = await db.scalar(select(m.SourceRevision).where(m.SourceRevision.asset_id == asset.id)
                             .order_by(m.SourceRevision.version.desc()).limit(1))
    if latest is None:
        raise NOT_FOUND
    sha, mime, uri, anchors = _material(text, docx)
    if sha == latest.sha256:
        raise ApiError(409, "SOURCE_UNCHANGED", "Nội dung giống bản hiện tại")
    await _insert_revision(db, asset.id, latest.version + 1, sha, mime, uri, anchors)
    await db.commit()
    return await source_out(db, asset)


async def list_sources(db: AsyncSession, user: CurrentUser) -> SourceList:
    assets = (await db.scalars(select(m.SourceAsset).where(_visible(user))
                               .order_by(m.SourceAsset.created_at.desc(), m.SourceAsset.title))).all()
    return SourceList(items=[await source_out(db, a) for a in assets])


async def get_source(db: AsyncSession, user: CurrentUser, source_id: UUID) -> SourceOut:
    asset = await db.scalar(select(m.SourceAsset).where(m.SourceAsset.id == source_id, _visible(user)))
    if asset is None:
        raise NOT_FOUND
    return await source_out(db, asset)


async def list_anchors(db: AsyncSession, user: CurrentUser, revision_id: UUID) -> AnchorList:
    ok = await db.scalar(select(m.SourceRevision.id).join(m.SourceAsset, m.SourceAsset.id == m.SourceRevision.asset_id)
                         .where(m.SourceRevision.id == revision_id, _visible(user)))
    if ok is None:
        raise NOT_FOUND
    rows = (await db.scalars(select(m.SourceAnchor).where(m.SourceAnchor.source_revision_id == revision_id)
                             .order_by(m.SourceAnchor.code))).all()
    return AnchorList(items=[AnchorOut(
        id=a.id, code=a.code, kind=a.kind, locator=a.locator, excerpt=a.excerpt,
        excerpt_hash=a.excerpt_hash, numbers=[float(n) for n in a.numbers]) for a in rows])


async def create_file_source(db: AsyncSession, user: CurrentUser, title: str, license_note: str | None, visibility: str,
                             data: bytes) -> SourceOut:
    """DOCX / PDF / XLSX / PPTX (type from magic bytes). A scanned PDF is stored as a FAILED revision (no anchors)."""
    if visibility == "SCHOOL" and not (license_note or "").strip():  # VAL-09
        raise ApiError(422, "LICENSE_REQUIRED", "Nguồn chia sẻ toàn trường cần ghi chú bản quyền")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ApiError(422, "FILE_TOO_LARGE", "Tệp vượt quá 10 MB")
    kind = detect_kind(data)
    cfg = get_settings()
    lim = Limits(cfg.source_max_pdf_pages, cfg.source_max_xlsx_sheets, cfg.source_max_xlsx_cells, cfg.source_max_pptx_slides,
                 cfg.source_parse_timeout_s, cfg.source_parse_mem_mb)
    status, anchors = "OK", []
    try:
        anchors = await parse_isolated(kind, data, lim)
    except ApiError as e:
        if e.code != "SCANNED_PDF":
            raise
        status = "FAILED"
    asset = m.SourceAsset(owner_id=user.id, title=title.strip(), license_note=license_note, visibility=visibility)
    db.add(asset)
    await db.flush()
    await _insert_revision(db, asset.id, 1, sha256_hex_bytes(data), MIME[kind], _store_docx(data, kind), anchors, status)
    await db.commit()
    return await source_out(db, asset)
