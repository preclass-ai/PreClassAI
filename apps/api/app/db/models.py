"""SQLAlchemy models. Enums are text + CHECK. Triggers live in alembic/versions/0001_triggers.sql."""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import DateTime


class Base(DeclarativeBase):
    pass


def _in(col: str, *values: str) -> CheckConstraint:
    vals = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{col} IN ({vals})", name=f"ck_{col}")


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))


def fk(target: str, nullable: bool = False) -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), ForeignKey(target), nullable=nullable)


def ts() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


def jsonb(default: str | None = None) -> Mapped[dict[str, Any]]:
    return mapped_column(JSONB, server_default=text(default) if default else None)


class AppUser(Base):
    __tablename__ = "app_user"
    __table_args__ = (
        _in("role", "TEACHER", "REVIEWER", "STUDENT", "ADMIN"),
        CheckConstraint("email IS NOT NULL OR login_code IS NOT NULL", name="ck_user_identity"),
    )
    id: Mapped[uuid.UUID] = pk()
    email: Mapped[str | None] = mapped_column(Text, unique=True)
    login_code: Mapped[str | None] = mapped_column(Text, unique=True)  # students: no email/phone
    display_name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"))
    created_at: Mapped[datetime] = ts()


class Session(Base):
    __tablename__ = "session"
    id: Mapped[uuid.UUID] = pk()
    token_hash: Mapped[str] = mapped_column(Text, unique=True)  # sha256 of the cookie value
    user_id: Mapped[uuid.UUID] = fk("app_user.id")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = ts()


class Class(Base):
    __tablename__ = "class"
    __table_args__ = (CheckConstraint("grade IN (10, 11)", name="ck_class_grade"),)
    id: Mapped[uuid.UUID] = pk()
    code: Mapped[str] = mapped_column(Text, unique=True)
    grade: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = ts()


class ClassMember(Base):
    __tablename__ = "class_member"
    __table_args__ = (UniqueConstraint("class_id", "user_id"), _in("role_in_class", "TEACHER", "STUDENT"))
    id: Mapped[uuid.UUID] = pk()
    class_id: Mapped[uuid.UUID] = fk("class.id")
    user_id: Mapped[uuid.UUID] = fk("app_user.id")
    role_in_class: Mapped[str] = mapped_column(Text)


class SourceAsset(Base):
    __tablename__ = "source_asset"
    __table_args__ = (_in("visibility", "PRIVATE", "SCHOOL"),)
    id: Mapped[uuid.UUID] = pk()
    owner_id: Mapped[uuid.UUID] = fk("app_user.id")
    title: Mapped[str] = mapped_column(Text)
    license_note: Mapped[str | None] = mapped_column(Text)
    visibility: Mapped[str] = mapped_column(Text, server_default="PRIVATE")
    created_at: Mapped[datetime] = ts()


class SourceRevision(Base):
    __tablename__ = "source_revision"
    __table_args__ = (UniqueConstraint("asset_id", "version"), _in("extract_status", "PENDING", "OK", "FAILED"))
    id: Mapped[uuid.UUID] = pk()
    asset_id: Mapped[uuid.UUID] = fk("source_asset.id")
    version: Mapped[int] = mapped_column(Integer)
    sha256: Mapped[str] = mapped_column(Text)
    mime: Mapped[str] = mapped_column(Text)
    file_uri: Mapped[str | None] = mapped_column(Text)
    extract_status: Mapped[str] = mapped_column(Text, server_default="PENDING")
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = ts()


class SourceAnchor(Base):
    __tablename__ = "source_anchor"
    __table_args__ = (
        UniqueConstraint("source_revision_id", "code"),
        _in("kind", "PARAGRAPH", "HEADING", "TABLE_CELL", "TABLE_ROW"),
    )
    id: Mapped[uuid.UUID] = pk()
    source_revision_id: Mapped[uuid.UUID] = fk("source_revision.id")
    code: Mapped[str] = mapped_column(Text)  # stable id: anc_<revision>_<seq>
    kind: Mapped[str] = mapped_column(Text)
    locator: Mapped[dict[str, Any]] = jsonb()
    excerpt: Mapped[str] = mapped_column(Text)
    excerpt_hash: Mapped[str] = mapped_column(Text)
    numbers: Mapped[list[Decimal]] = mapped_column(ARRAY(Numeric), server_default=text("'{}'"))


class Lesson(Base):
    __tablename__ = "lesson"
    __table_args__ = (CheckConstraint("grade IN (10, 11)", name="ck_lesson_grade"), _in("subject", "GEOGRAPHY"))
    id: Mapped[uuid.UUID] = pk()
    author_id: Mapped[uuid.UUID] = fk("app_user.id")
    subject: Mapped[str] = mapped_column(Text, server_default="GEOGRAPHY")
    grade: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    goal: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()


class LessonRevision(Base):
    __tablename__ = "lesson_revision"
    __table_args__ = (
        UniqueConstraint("lesson_id", "revision_no"),
        _in("state", "DRAFT", "IN_REVIEW", "PUBLISHED", "SUPERSEDED"),
    )
    id: Mapped[uuid.UUID] = pk()
    lesson_id: Mapped[uuid.UUID] = fk("lesson.id")
    revision_no: Mapped[int] = mapped_column(Integer)
    state: Mapped[str] = mapped_column(Text, server_default="DRAFT")
    base_revision_id: Mapped[uuid.UUID | None] = fk("lesson_revision.id", nullable=True)
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))  # optimistic lock
    created_at: Mapped[datetime] = ts()


class LessonSource(Base):
    __tablename__ = "lesson_source"
    __table_args__ = (UniqueConstraint("lesson_revision_id", "source_revision_id"),)
    id: Mapped[uuid.UUID] = pk()
    lesson_revision_id: Mapped[uuid.UUID] = fk("lesson_revision.id")
    source_revision_id: Mapped[uuid.UUID] = fk("source_revision.id")


class LessonReviewer(Base):
    __tablename__ = "lesson_reviewer"
    __table_args__ = (UniqueConstraint("lesson_id", "reviewer_id"),)
    id: Mapped[uuid.UUID] = pk()
    lesson_id: Mapped[uuid.UUID] = fk("lesson.id")
    reviewer_id: Mapped[uuid.UUID] = fk("app_user.id")


class ContentBlock(Base):
    __tablename__ = "content_block"
    __table_args__ = (
        _in(
            "transformation", "ORIGINAL", "PARAPHRASED", "SYNTHESISED", "AI_PROPOSED", "TEACHER_AUTHORED"
        ),
        _in(
            "review_status", "UNREVIEWED", "AUTO_CHECKED", "FLAGGED", "APPROVED", "REVIEW_AGAIN", "REJECTED"
        ),
    )
    id: Mapped[uuid.UUID] = pk()
    revision_id: Mapped[uuid.UUID] = fk("lesson_revision.id")
    kind: Mapped[str] = mapped_column(Text)
    parent_id: Mapped[uuid.UUID | None] = fk("content_block.id", nullable=True)
    position: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = jsonb()
    content_hash: Mapped[str] = mapped_column(Text)
    transformation: Mapped[str] = mapped_column(Text)
    review_status: Mapped[str] = mapped_column(Text, server_default="UNREVIEWED")
    no_source_reason: Mapped[str | None] = mapped_column(Text)
    is_factual: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    version: Mapped[int] = mapped_column(Integer, server_default=text("1"))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = ts()


class ProvenanceLink(Base):
    __tablename__ = "provenance_link"
    __table_args__ = (
        UniqueConstraint("block_id", "anchor_id"),
        _in("relation", "derived_from", "quotes", "supports"),
        _in("status", "VERIFIED", "UNRESOLVED"),
    )
    id: Mapped[uuid.UUID] = pk()
    block_id: Mapped[uuid.UUID] = fk("content_block.id")
    anchor_id: Mapped[uuid.UUID] = fk("source_anchor.id")
    relation: Mapped[str] = mapped_column(Text)
    rationale: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text, server_default="VERIFIED")


class BlockDependency(Base):
    __tablename__ = "block_dependency"
    __table_args__ = (
        UniqueConstraint("block_id", "depends_on_block_id"),
        _in("kind", "ANSWER_OF", "EXPLANATION_OF", "FEEDBACK_OF", "LABEL_OF"),
    )
    id: Mapped[uuid.UUID] = pk()
    block_id: Mapped[uuid.UUID] = fk("content_block.id")
    depends_on_block_id: Mapped[uuid.UUID] = fk("content_block.id")
    kind: Mapped[str] = mapped_column(Text)


class TransformationEvent(Base):
    __tablename__ = "transformation_event"
    __table_args__ = (
        _in("actor_type", "AI", "TEACHER", "SYSTEM"),
        _in("operation", "GENERATE", "EDIT", "REGENERATE", "SOURCE_REPLACED"),
    )
    id: Mapped[uuid.UUID] = pk()
    block_id: Mapped[uuid.UUID] = fk("content_block.id")
    actor_type: Mapped[str] = mapped_column(Text)
    actor_id: Mapped[uuid.UUID | None] = fk("app_user.id", nullable=True)
    operation: Mapped[str] = mapped_column(Text)
    before_hash: Mapped[str | None] = mapped_column(Text)
    after_hash: Mapped[str] = mapped_column(Text)
    generator_version: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()


class ValidationResult(Base):
    __tablename__ = "validation_result"
    __table_args__ = (
        CheckConstraint("rule ~ '^VAL-0[1-9]$'", name="ck_validation_rule"),
        _in("severity", "BLOCKER", "WARNING"),
        _in("outcome", "PASS", "FAIL"),
    )
    id: Mapped[uuid.UUID] = pk()
    block_id: Mapped[uuid.UUID] = fk("content_block.id")
    rule: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    outcome: Mapped[str] = mapped_column(Text)
    evidence: Mapped[dict[str, Any]] = jsonb("'{}'")
    method: Mapped[str] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()


class ReviewEvent(Base):
    __tablename__ = "review_event"
    __table_args__ = (_in("action", "APPROVE", "REJECT", "REQUEST_CHANGES"),)
    id: Mapped[uuid.UUID] = pk()
    block_id: Mapped[uuid.UUID] = fk("content_block.id")
    content_hash: Mapped[str] = mapped_column(Text)
    source_hashes: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default=text("'{}'"))
    reviewer_id: Mapped[uuid.UUID] = fk("app_user.id")
    action: Mapped[str] = mapped_column(Text)
    note: Mapped[str | None] = mapped_column(Text)
    # clock_timestamp(): strictly ordered inside one transaction ("latest event" lookups)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("clock_timestamp()")
    )


class GenerationJob(Base):
    __tablename__ = "generation_job"
    __table_args__ = (
        _in("output_type", "WORKSHEET", "FLASHCARDS"),
        _in("status", "QUEUED", "RUNNING", "SUCCEEDED", "FAILED"),
    )
    id: Mapped[uuid.UUID] = pk()
    revision_id: Mapped[uuid.UUID] = fk("lesson_revision.id")
    output_type: Mapped[str] = mapped_column(Text)
    params: Mapped[dict[str, Any]] = jsonb("'{}'")
    status: Mapped[str] = mapped_column(Text, server_default="QUEUED")
    error: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    tokens_in: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    tokens_out: Mapped[int] = mapped_column(Integer, server_default=text("0"))
    created_by: Mapped[uuid.UUID | None] = fk("app_user.id", nullable=True)
    created_at: Mapped[datetime] = ts()


class UsageDaily(Base):
    __tablename__ = "usage_daily"
    day: Mapped[datetime] = mapped_column(DateTime(timezone=False), primary_key=True)
    tokens: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))


class PublishedVersion(Base):
    __tablename__ = "published_version"
    __table_args__ = (_in("state", "ACTIVE", "WITHDRAWN"),)
    id: Mapped[uuid.UUID] = pk()
    lesson_revision_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("lesson_revision.id"), unique=True
    )
    snapshot: Mapped[dict[str, Any]] = jsonb()
    snapshot_hash: Mapped[str] = mapped_column(Text)
    published_by: Mapped[uuid.UUID] = fk("app_user.id")
    state: Mapped[str] = mapped_column(Text, server_default="ACTIVE")
    withdraw_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = ts()


class Assignment(Base):
    __tablename__ = "assignment"
    id: Mapped[uuid.UUID] = pk()
    published_version_id: Mapped[uuid.UUID] = fk("published_version.id")
    class_id: Mapped[uuid.UUID] = fk("class.id")
    open_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = ts()


class StudentAttempt(Base):
    __tablename__ = "student_attempt"
    # One attempt per (assignment, student, item); request_id is idempotency only (D-001 #9).
    __table_args__ = (UniqueConstraint("assignment_id", "student_id", "item_block_id"),)
    id: Mapped[uuid.UUID] = pk()
    assignment_id: Mapped[uuid.UUID] = fk("assignment.id")
    student_id: Mapped[uuid.UUID] = fk("app_user.id")
    item_block_id: Mapped[uuid.UUID] = fk("content_block.id")
    answer: Mapped[dict[str, Any]] = jsonb()
    is_correct: Mapped[bool | None] = mapped_column(Boolean)  # null for SHORT / rubric
    request_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), unique=True)
    created_at: Mapped[datetime] = ts()


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[uuid.UUID] = pk()
    actor_id: Mapped[uuid.UUID | None] = fk("app_user.id", nullable=True)
    action: Mapped[str] = mapped_column(Text)
    resource_type: Mapped[str] = mapped_column(Text)
    resource_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    meta: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, server_default=text("'{}'"))  # no content
    created_at: Mapped[datetime] = ts()
