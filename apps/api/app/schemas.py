"""API contract (v0). Pydantic models are the single source of the OpenAPI document.

JSON is camelCase on the wire. Examples use the same ids as the seed (app.ids), so a mock server and
the real seeded backend return matching shapes. After the v1 freeze: add fields, never rename/remove.
"""

from datetime import date, datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel

from app.ids import uid

# ---------------------------------------------------------------- shared example values
_L = "dan-so-vung"
T0 = "2026-11-14T09:00:00+07:00"
T1 = "2026-11-15T09:00:00+07:00"
H = "9f2c1b7a4e5d63c8a0b1d2e3f405162738495a6b7c8d9e0f1a2b3c4d5e6f7a8b"
H2 = "1a2b3c4d5e6f708192a3b4c5d6e7f8091a2b3c4d5e6f708192a3b4c5d6e7f809"
I = {  # noqa: E741
    "teacher": str(uid("user:gv.dia")), "student": str(uid("user:HS10-01")), "reviewer": str(uid("user:reviewer")),
    "class": str(uid("class:10A1")), "asset": str(uid(f"{_L}:asset")), "srcrev": str(uid(f"{_L}:srcrev")),
    "lesson": str(uid(f"{_L}:lesson")), "lrev": str(uid(f"{_L}:lrev")), "pub": str(uid(f"{_L}:published")),
    "assign": str(uid(f"{_L}:assignment")), "job": str(uid(f"{_L}:job")),
    "q1": str(uid(f"{_L}:blk:q1")), "q1k": str(uid(f"{_L}:blk:q1k")), "q1e": str(uid(f"{_L}:blk:q1e")),
    "q1o0": str(uid(f"{_L}:blk:q1o0")), "p1": str(uid(f"{_L}:blk:p1")), "df": str(uid(f"{_L}:blk:df")),
    "anchor": str(uid(f"{_L}:anchor:r1c1")), "event": str(uid("example:event")),
    "request": str(uid("example:request")),
}
ANCHOR_CODE = f"anc_{I['srcrev'][:8]}_007"


def ex(*examples: dict[str, Any]) -> ConfigDict:
    return ConfigDict(json_schema_extra={"examples": list(examples)})


def e0(model: type[BaseModel]) -> dict[str, Any]:
    """First example of a model (reuse it inside other examples)."""
    return model.model_config["json_schema_extra"]["examples"][0]  # type: ignore[index,return-value]


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# ---------------------------------------------------------------- enums (text + CHECK in the DB)
Role = Literal["TEACHER", "REVIEWER", "STUDENT", "ADMIN"]
Visibility = Literal["PRIVATE", "SCHOOL"]
ExtractStatus = Literal["PENDING", "OK", "FAILED"]
AnchorKind = Literal["PARAGRAPH", "HEADING", "TABLE_CELL", "TABLE_ROW"]
RevisionState = Literal["DRAFT", "IN_REVIEW", "PUBLISHED", "SUPERSEDED"]
Transformation = Literal["ORIGINAL", "PARAPHRASED", "SYNTHESISED", "AI_PROPOSED", "TEACHER_AUTHORED"]
ReviewStatus = Literal["UNREVIEWED", "AUTO_CHECKED", "FLAGGED", "APPROVED", "REVIEW_AGAIN", "REJECTED"]
BlockKind = Literal[
    "heading", "paragraph", "data_fact", "instruction", "worksheet_item", "option", "answer_key", "explanation",
    "card_front", "card_back",
]
Relation = Literal["derived_from", "quotes", "supports"]
LinkStatus = Literal["VERIFIED", "UNRESOLVED"]
OutputType = Literal["WORKSHEET", "FLASHCARDS"]
Skill = Literal["READ_TABLE", "COMPARE", "CALCULATE", "EXPLAIN"]
ItemType = Literal["MCQ", "SHORT", "NUMERIC"]
JobStatus = Literal["QUEUED", "RUNNING", "SUCCEEDED", "FAILED"]
ReviewAction = Literal["APPROVE", "REJECT", "REQUEST_CHANGES"]
Severity = Literal["BLOCKER", "WARNING"]
Outcome = Literal["PASS", "FAIL"]
PublishedState = Literal["ACTIVE", "WITHDRAWN"]
ActorType = Literal["AI", "TEACHER", "SYSTEM"]
Operation = Literal["GENERATE", "EDIT", "REGENERATE", "SOURCE_REPLACED"]


# ---------------------------------------------------------------- errors (RFC 9457)
class ProblemFieldError(ApiModel):
    loc: list[str | int]
    type: str


class Problem(ApiModel):
    """Every non-2xx response. Branch on `code`, never on `title`/`detail` (Vietnamese text may change)."""

    type: str
    title: str
    status: int
    detail: str = ""
    code: str = Field(description="Stable machine code, see API_GUIDE error table.")
    errors: list[ProblemFieldError] | None = None
    block_ids: list[UUID] | None = Field(None, description="PUBLISH_BLOCKED: blocks that stop the publish.")
    model_config = ex({
        "type": "https://preclass.local/problems/stale_review", "title": "Nội dung đã thay đổi sau khi bạn xem",
        "status": 409, "detail": "", "code": "STALE_REVIEW"})


class Page(ApiModel):
    """List envelope. `nextCursor` is reserved (always null in v1; additive pagination later)."""

    next_cursor: str | None = None


# ---------------------------------------------------------------- auth, users, classes
class LoginRequest(ApiModel):
    identifier: str = Field(description="Teacher/admin email, or student login code (e.g. HS10-01).")
    password: str
    model_config = ex({"identifier": "gv.dia@preclass.local", "password": "preclass-demo"})


class AuthConfig(ApiModel):
    guest_enabled: bool = Field(description="True when anonymous guest access is switched on (GUEST_ACCESS_ENABLED).")
    chat_enabled: bool = Field(False, description="True when Habit (hints + chat) is on (CHAT_ENABLED).")
    personalization_enabled: bool = Field(False, description="True when student-chosen options and focus mode are on.")
    model_config = ex({"guestEnabled": True, "chatEnabled": False, "personalizationEnabled": False})


class GuestRequest(ApiModel):
    lesson_key: str | None = Field(default=None, max_length=80, description="Optional lesson slug (e.g. dan-so-vung): "
                                   "the response then carries the matching assignmentId so the client can open it.")
    model_config = ex({"lessonKey": "dan-so-vung"})


class GuestResumeRequest(ApiModel):
    survey_code: str = Field(max_length=20, description="Code shown to the guest, e.g. KS-7H4P (case-insensitive).")
    lesson_key: str | None = Field(default=None, max_length=80, description="Same as on POST /auth/guest.")
    model_config = ex({"surveyCode": "KS-7H4P", "lessonKey": "dan-so-vung"})


class UserOut(ApiModel):
    id: UUID
    role: Role
    display_name: str
    email: str | None = None
    login_code: str | None = None
    class_ids: list[UUID] = []
    is_guest: bool = False
    survey_code: str | None = Field(default=None, description="Anonymous survey code (guests only), e.g. KS-7H4P.")
    model_config = ex({
        "id": I["teacher"], "role": "TEACHER", "displayName": "Cô Địa Lí (minh họa)",
        "email": "gv.dia@preclass.local", "loginCode": None, "classIds": [I["class"]]})


class SurveyStats(ApiModel):
    active_guests: int = Field(description="Guests seen or created in the last 14 days.")
    created_last_hour: int
    max_active: int = Field(description="GUEST_MAX_ACTIVE.")
    create_per_hour_per_ip: int = Field(description="GUEST_CREATE_PER_HOUR.")
    chat_total: int = Field(0, description="Habit replies stored so far.")
    chat_fallback_rate: float = Field(0, description="Share of LLM attempts that fell back to the rule reply.")
    chat_blocked: dict[str, int] = Field(default_factory=dict, description="Replies per blocked_reason.")
    chat_tokens_in: int = 0
    chat_tokens_out: int = 0
    model_config = ex({"activeGuests": 42, "createdLastHour": 12, "maxActive": 500, "createPerHourPerIp": 60,
                       "chatTotal": 120, "chatFallbackRate": 0.0, "chatBlocked": {"ANSWER_REQUEST": 7},
                       "chatTokensIn": 0, "chatTokensOut": 0})


class GuestOut(ApiModel):
    user: UserOut
    survey_code: str
    assignment_id: UUID | None = Field(default=None, description="Assignment of the requested lesson in the survey class.")
    model_config = ex({"user": {"id": I["student"], "role": "STUDENT",
                                "displayName": "Khách 7H4P", "loginCode": "KS-7H4P", "classIds": [I["class"]],
                                "isGuest": True, "surveyCode": "KS-7H4P"}, "surveyCode": "KS-7H4P", "assignmentId": None})


class ClassOut(ApiModel):
    id: UUID
    code: str
    grade: Literal[10, 11]
    student_count: int
    model_config = ex({"id": I["class"], "code": "10A1", "grade": 10, "studentCount": 15})


class ClassList(Page):
    items: list[ClassOut]
    model_config = ex({"items": [{"id": I["class"], "code": "10A1", "grade": 10, "studentCount": 15}],
                       "nextCursor": None})


class AuditLogOut(ApiModel):
    id: UUID
    actor_id: UUID | None
    action: str
    resource_type: str
    resource_id: UUID | None
    metadata: dict[str, Any] = {}
    created_at: datetime
    model_config = ex({"id": I["event"], "actorId": I["teacher"], "action": "INSPECT_PROVENANCE",
                       "resourceType": "content_block", "resourceId": I["q1"], "metadata": {}, "createdAt": T0})


class AuditLogList(Page):
    items: list[AuditLogOut]
    model_config = ex({"items": [e0(AuditLogOut)], "nextCursor": None})


# ---------------------------------------------------------------- sources
class SourceRevisionOut(ApiModel):
    id: UUID
    asset_id: UUID
    version: int
    sha256: str
    mime: str
    extract_status: ExtractStatus
    extract_error: str | None = Field(None, description="`SCANNED_PDF` when `extractStatus` is FAILED.")
    anchor_count: int
    created_at: datetime
    model_config = ex({"id": I["srcrev"], "assetId": I["asset"], "version": 1, "sha256": H, "mime": "text/plain",
                       "extractStatus": "OK", "extractError": None, "anchorCount": 11, "createdAt": T0})


_SRC_REV = e0(SourceRevisionOut)


class SourceOut(ApiModel):
    id: UUID
    title: str
    license_note: str | None
    visibility: Visibility
    owner_id: UUID
    latest_revision: SourceRevisionOut
    created_at: datetime
    model_config = ex({
        "id": I["asset"], "title": "Phân bố dân cư theo vùng (dan-so-vung)",
        "licenseNote": "DỮ LIỆU MINH HỌA: số liệu giả, không phải số liệu chính thức.", "visibility": "SCHOOL",
        "ownerId": I["teacher"], "latestRevision": _SRC_REV, "createdAt": T0})


_SRC = e0(SourceOut)


class SourceList(Page):
    items: list[SourceOut]
    model_config = ex({"items": [_SRC], "nextCursor": None})


class SourceCreateText(ApiModel):
    """JSON body of POST /sources. For a DOCX use POST /sources/docx (multipart)."""

    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=200_000, description="Paragraphs separated by a blank line.")
    license_note: str | None = None
    visibility: Visibility = "PRIVATE"
    model_config = ex({"title": "Bài đọc mẫu", "text": "Tiêu đề\n\nĐoạn một.\n\nĐoạn hai.",
                       "licenseNote": "DỮ LIỆU MINH HỌA", "visibility": "PRIVATE"})


class SourceRevisionCreateText(ApiModel):
    text: str = Field(min_length=1, max_length=200_000)
    model_config = ex({"text": "Tiêu đề\n\nĐoạn một (đã sửa).\n\nĐoạn hai."})


class AnchorOut(ApiModel):
    id: UUID
    code: str = Field(description="Stable id like anc_<revision>_<seq>; shown in the Source Inspector.")
    kind: AnchorKind
    locator: dict[str, Any] = Field(description='{"para_index": n} or {"table": t, "row": r, "col": c}')
    excerpt: str
    excerpt_hash: str
    numbers: list[float] = []
    model_config = ex({"id": I["anchor"], "code": ANCHOR_CODE, "kind": "TABLE_CELL",
                       "locator": {"table": 0, "row": 1, "col": 1}, "excerpt": "23,2", "excerptHash": H,
                       "numbers": [23.2]})


class AnchorList(Page):
    items: list[AnchorOut]
    model_config = ex({"items": [e0(AnchorOut)], "nextCursor": None})


# ---------------------------------------------------------------- lessons and revisions
class BlockCounts(ApiModel):
    total: int = 0
    approved: int = 0
    flagged: int = 0
    review_again: int = 0
    unreviewed: int = 0
    auto_checked: int = 0
    rejected: int = 0


class RevisionOut(ApiModel):
    id: UUID
    lesson_id: UUID
    revision_no: int
    state: RevisionState
    version: int = Field(description="Optimistic lock: send back on publish / source change.")
    source_revision_ids: list[UUID]
    newer_source_available: bool = Field(description="A source of this revision has a newer version.")
    counts: BlockCounts
    created_at: datetime
    model_config = ex({
        "id": I["lrev"], "lessonId": I["lesson"], "revisionNo": 1, "state": "DRAFT", "version": 3,
        "sourceRevisionIds": [I["srcrev"]], "newerSourceAvailable": False,
        "counts": {"total": 14, "approved": 12, "flagged": 0, "reviewAgain": 1, "unreviewed": 0,
                   "autoChecked": 1, "rejected": 0}, "createdAt": T0})


_REV = e0(RevisionOut)


class LessonCreate(ApiModel):
    title: str = Field(min_length=1, max_length=200)
    grade: Literal[10, 11]
    goal: str | None = None
    source_revision_ids: list[UUID] = Field(min_length=1)
    model_config = ex({"title": "Phân bố dân cư theo vùng", "grade": 10,
                       "goal": "Đọc và so sánh số dân giữa các vùng.", "sourceRevisionIds": [I["srcrev"]]})


class LessonOut(ApiModel):
    id: UUID
    title: str
    grade: Literal[10, 11]
    subject: Literal["GEOGRAPHY"] = "GEOGRAPHY"
    goal: str | None
    author_id: UUID
    current_revision: RevisionOut
    published_version_id: UUID | None = None
    created_at: datetime
    model_config = ex({
        "id": I["lesson"], "title": "Phân bố dân cư theo vùng", "grade": 10, "subject": "GEOGRAPHY",
        "goal": "Đọc và so sánh số dân giữa các vùng từ bảng số liệu.", "authorId": I["teacher"],
        "currentRevision": _REV, "publishedVersionId": None, "createdAt": T0})


_LESSON = e0(LessonOut)


class LessonList(Page):
    items: list[LessonOut]
    model_config = ex({"items": [_LESSON], "nextCursor": None})


class RevisionSourcesUpdate(ApiModel):
    """PUT /revisions/{id}/sources — DRAFT only. Anchors are re-matched by excerpt_hash / locator."""

    source_revision_ids: list[UUID] = Field(min_length=1)
    version: int
    model_config = ex({"sourceRevisionIds": [I["srcrev"]], "version": 3})


class RevisionSourcesResult(ApiModel):
    revision: RevisionOut
    matched_links: int
    unresolved_links: int = Field(description="Links that could not be re-matched; blocks go to REVIEW_AGAIN.")
    model_config = ex({"revision": _REV, "matchedLinks": 21, "unresolvedLinks": 0})


class DiffSummary(ApiModel):
    added: int = 0
    changed: int = 0
    removed: int = 0


class HistoryRevision(ApiModel):
    revision_id: UUID
    revision_no: int
    state: RevisionState
    published_at: datetime | None = None
    block_count: int
    diff_summary: DiffSummary | None = Field(None, description="vs previous revision; may be null in v1.")


class HistoryEvent(ApiModel):
    at: datetime
    actor_type: ActorType
    actor_id: UUID | None = None
    operation: Operation | Literal["REVIEW", "PUBLISH", "WITHDRAW"]
    block_id: UUID | None = None
    summary: str | None = None


class LessonHistory(ApiModel):
    revisions: list[HistoryRevision]
    events: list[HistoryEvent]
    model_config = ex({
        "revisions": [{"revisionId": I["lrev"], "revisionNo": 1, "state": "PUBLISHED", "publishedAt": T1,
                       "blockCount": 14, "diffSummary": None}],
        "events": [{"at": T0, "actorType": "AI", "actorId": None, "operation": "GENERATE", "blockId": I["q1"],
                    "summary": None}]})


# ---------------------------------------------------------------- generation
class GenerateRequest(ApiModel):
    output_type: OutputType
    n_items: int = Field(5, ge=1, le=20)
    focus_skills: list[Skill] = []
    mode: Literal["initial", "append"] = Field(
        "initial", description="initial: only when the revision has no blocks. append: add to existing blocks.")
    model_config = ex({"outputType": "WORKSHEET", "nItems": 5, "focusSkills": ["READ_TABLE", "COMPARE"],
                       "mode": "initial"})


class JobAccepted(ApiModel):
    job_id: UUID
    model_config = ex({"jobId": I["job"]})


class JobOut(ApiModel):
    id: UUID
    revision_id: UUID
    output_type: OutputType
    status: JobStatus
    error: str | None = None
    block_count: int = 0
    model: str | None = None
    created_at: datetime
    model_config = ex({"id": I["job"], "revisionId": I["lrev"], "outputType": "WORKSHEET", "status": "SUCCEEDED",
                       "error": None, "blockCount": 14, "model": "mock-v1", "createdAt": T0})


# ---------------------------------------------------------------- blocks
class Derivation(ApiModel):
    """Computed number (PR-07): server recomputes with Decimal and compares. Operands: anchor code or number."""

    op: Literal["sum", "diff", "ratio", "percent"]
    operands: list[str | float]


class HeadingPayload(ApiModel):
    text: str


class ParagraphPayload(ApiModel):
    text: str


class InstructionPayload(ApiModel):
    text: str


class DataFactPayload(ApiModel):
    label: str
    value: float
    unit: str
    period: str
    region: str
    note: str | None = None


class WorksheetItemPayload(ApiModel):
    stem: str
    item_type: ItemType
    skill: Skill


class OptionPayload(ApiModel):
    label: Literal["A", "B", "C", "D"]
    text: str


class AnswerKeyPayload(ApiModel):
    """MCQ: `correct`. NUMERIC: `value`+`unit`+`tolerance` (+`derivation`). SHORT: `rubricPoints`."""

    correct: Literal["A", "B", "C", "D"] | None = None
    value: float | None = None
    unit: str | None = None
    tolerance: float | None = None
    rubric_points: list[str] | None = None
    derivation: Derivation | None = None


class ExplanationPayload(ApiModel):
    text: str
    derivation: Derivation | None = None


class CardPayload(ApiModel):
    text: str


BlockPayload = (
    DataFactPayload | WorksheetItemPayload | AnswerKeyPayload | OptionPayload | ExplanationPayload
    | HeadingPayload | ParagraphPayload | InstructionPayload | CardPayload
)


class BlockOut(ApiModel):
    """`payload` shape depends on `kind` (see DATA_MODEL.md). Blocks come as a flat list: use parentId/position."""

    id: UUID
    revision_id: UUID
    kind: BlockKind
    parent_id: UUID | None
    position: int
    payload: BlockPayload
    content_hash: str = Field(description="Send back in POST /blocks/{id}/reviews (approval is bound to it).")
    transformation: Transformation
    review_status: ReviewStatus
    no_source_reason: str | None
    is_factual: bool
    version: int = Field(description="Optimistic lock: send back in PATCH.")
    link_count: int = 0
    blocker_count: int = Field(0, description="Failed BLOCKER validations at the current hash.")
    warning_count: int = 0
    model_config = ex({
        "id": I["q1"], "revisionId": I["lrev"], "kind": "worksheet_item", "parentId": None, "position": 6,
        "payload": {"stem": "Theo bảng số liệu, vùng nào có số dân cao nhất?", "itemType": "MCQ",
                    "skill": "COMPARE"},
        "contentHash": H, "transformation": "AI_PROPOSED", "reviewStatus": "APPROVED",
        "noSourceReason": "Nội dung sư phạm do AI đề xuất, không lấy trực tiếp từ nguồn.", "isFactual": False,
        "version": 1, "linkCount": 0, "blockerCount": 0, "warningCount": 0})


_BLOCK = e0(BlockOut)


class BlockList(Page):
    items: list[BlockOut]
    model_config = ex({"items": [_BLOCK], "nextCursor": None})


class BlockCreate(ApiModel):
    """Adds a TEACHER_AUTHORED block. The server checks that `payload` matches `kind`."""

    kind: BlockKind
    parent_id: UUID | None = None
    position: int | None = Field(None, description="Insert position; null appends.")
    payload: BlockPayload
    is_factual: bool = False
    model_config = ex({"kind": "paragraph", "parentId": None, "position": None,
                       "payload": {"text": "Nhận xét của giáo viên."}, "isFactual": False})


class BlockPatch(ApiModel):
    payload: BlockPayload
    version: int
    model_config = ex({"payload": {"text": "Nhận xét đã chỉnh sửa."}, "version": 1})


# ---------------------------------------------------------------- provenance (Source Inspector)
class AnchorRef(ApiModel):
    anchor_id: UUID
    code: str
    kind: AnchorKind
    locator: dict[str, Any]
    excerpt: str
    source_revision_id: UUID
    source_title: str
    source_version: int


class ProvenanceLinkOut(ApiModel):
    id: UUID
    anchor: AnchorRef
    relation: Relation
    rationale: str | None = None
    status: LinkStatus


class TransformationEventOut(ApiModel):
    id: UUID
    actor_type: ActorType
    actor_id: UUID | None = None
    operation: Operation
    before_hash: str | None = None
    after_hash: str
    generator_version: str | None = None
    created_at: datetime


class ValidationResultOut(ApiModel):
    id: UUID
    rule: str = Field(description="VAL-01 … VAL-10")
    severity: Severity
    outcome: Outcome
    evidence: dict[str, Any] = {}
    method: str
    content_hash: str
    is_current: bool = Field(description="True when content_hash equals the block's current hash.")
    created_at: datetime


class ReviewEventOut(ApiModel):
    id: UUID
    action: ReviewAction
    content_hash: str
    source_hashes: list[str]
    reviewer_id: UUID
    reviewer_name: str
    note: str | None = None
    is_valid: bool = Field(description="APPROVE whose hashes still match the current block and sources.")
    created_at: datetime


class ProvenanceOut(ApiModel):
    block: BlockOut
    links: list[ProvenanceLinkOut]
    events: list[TransformationEventOut]
    validations: list[ValidationResultOut]
    reviews: list[ReviewEventOut]
    model_config = ex({
        "block": _BLOCK,
        "links": [{"id": I["event"], "anchor": {
            "anchorId": I["anchor"], "code": ANCHOR_CODE, "kind": "TABLE_CELL",
            "locator": {"table": 0, "row": 1, "col": 1}, "excerpt": "23,2", "sourceRevisionId": I["srcrev"],
            "sourceTitle": "Phân bố dân cư theo vùng (dan-so-vung)", "sourceVersion": 1},
            "relation": "derived_from", "rationale": "Dữ liệu minh họa", "status": "VERIFIED"}],
        "events": [{"id": I["event"], "actorType": "AI", "actorId": None, "operation": "GENERATE",
                    "beforeHash": None, "afterHash": H, "generatorVersion": "mock-v1", "createdAt": T0}],
        "validations": [{"id": I["event"], "rule": "VAL-04", "severity": "BLOCKER", "outcome": "PASS",
                         "evidence": {}, "method": "rule", "contentHash": H, "isCurrent": True, "createdAt": T0}],
        "reviews": [{"id": I["event"], "action": "APPROVE", "contentHash": H, "sourceHashes": [H2],
                     "reviewerId": I["teacher"], "reviewerName": "Cô Địa Lí (minh họa)", "note": None,
                     "isValid": True, "createdAt": T1}]})


class LinkIn(ApiModel):
    anchor_id: UUID
    relation: Relation
    rationale: str | None = None


class ProvenanceUpdate(ApiModel):
    """Either `links` or `noSourceReason`. The server verifies every anchor belongs to the lesson's sources."""

    links: list[LinkIn] | None = None
    no_source_reason: str | None = None
    version: int
    model_config = ex({"links": [{"anchorId": I["anchor"], "relation": "derived_from", "rationale": None}],
                       "noSourceReason": None, "version": 1})


# ---------------------------------------------------------------- validation, review, publish
class BlockValidationSummary(ApiModel):
    block_id: UUID
    review_status: ReviewStatus
    failed_rules: list[str]


class ValidateOut(ApiModel):
    revision_id: UUID
    blocker_count: int
    warning_count: int
    blocks: list[BlockValidationSummary]
    model_config = ex({"revisionId": I["lrev"], "blockerCount": 1, "warningCount": 0,
                       "blocks": [{"blockId": I["q1e"], "reviewStatus": "FLAGGED", "failedRules": ["VAL-03"]}]})


class ReviewQueue(Page):
    """Sorted FLAGGED, REVIEW_AGAIN, UNREVIEWED."""

    items: list[BlockOut]
    model_config = ex({"items": [_BLOCK], "nextCursor": None})


class ReviewRequest(ApiModel):
    action: ReviewAction
    content_hash: str = Field(description="The hash the reviewer saw; stale → 409 STALE_REVIEW.")
    note: str | None = None
    model_config = ex({"action": "APPROVE", "contentHash": H, "note": None})


class ReviewOut(ApiModel):
    block: BlockOut
    review_event_id: UUID
    model_config = ex({"block": _BLOCK, "reviewEventId": I["event"]})


class PublishCheckItem(ApiModel):
    code: Literal["ALL_APPROVED", "NO_BLOCKERS", "SOURCES_VALID", "HAS_ITEMS"]
    ok: bool
    message: str
    block_ids: list[UUID] = []


class PublishCheckOut(ApiModel):
    can_publish: bool
    items: list[PublishCheckItem]
    model_config = ex({"canPublish": False, "items": [
        {"code": "ALL_APPROVED", "ok": False, "message": "Còn 2 khối chưa được duyệt.",
         "blockIds": [I["q1e"], I["p1"]]},
        {"code": "NO_BLOCKERS", "ok": True, "message": "Không còn cảnh báo chặn.", "blockIds": []}]})


class PublishRequest(ApiModel):
    confirm_checked: bool = Field(description="Must be true: the teacher confirms they checked the content.")
    version: int
    model_config = ex({"confirmChecked": True, "version": 3})


class PublishedOut(ApiModel):
    id: UUID
    lesson_revision_id: UUID
    lesson_title: str
    state: PublishedState
    snapshot_hash: str
    published_by: UUID
    published_at: datetime
    withdraw_reason: str | None = None
    model_config = ex({"id": I["pub"], "lessonRevisionId": I["lrev"], "lessonTitle": "Phân bố dân cư theo vùng",
                       "state": "ACTIVE", "snapshotHash": H2, "publishedBy": I["teacher"], "publishedAt": T1,
                       "withdrawReason": None})


class WithdrawRequest(ApiModel):
    reason: str = Field(min_length=3, max_length=500)
    model_config = ex({"reason": "Phát hiện sai số liệu ở câu 2."})


class AssignmentCreate(ApiModel):
    class_id: UUID
    open_at: datetime
    due_at: datetime
    model_config = ex({"classId": I["class"], "openAt": T1, "dueAt": "2026-11-30T23:59:00+07:00"})


class AssignmentOut(ApiModel):
    id: UUID
    published_version_id: UUID
    class_id: UUID
    class_code: str
    lesson_title: str
    open_at: datetime
    due_at: datetime
    model_config = ex({"id": I["assign"], "publishedVersionId": I["pub"], "classId": I["class"],
                       "classCode": "10A1", "lessonTitle": "Phân bố dân cư theo vùng", "openAt": T1,
                       "dueAt": "2026-11-30T23:59:00+07:00"})


class AssignmentList(Page):
    items: list[AssignmentOut]
    model_config = ex({"items": [e0(AssignmentOut)], "nextCursor": None})


class ProgressItem(ApiModel):
    item_block_id: UUID
    stem: str
    answered_count: int
    first_attempt_correct_rate: float | None = Field(None, description="0..1; null when nobody answered.")


class ProgressOut(ApiModel):
    assignment_id: UUID
    student_count: int
    items: list[ProgressItem]
    model_config = ex({"assignmentId": I["assign"], "studentCount": 15, "items": [
        {"itemBlockId": I["q1"], "stem": "Theo bảng số liệu, vùng nào có số dân cao nhất?", "answeredCount": 12,
         "firstAttemptCorrectRate": 0.75}]})


# ---------------------------------------------------------------- student (PR-08: whitelist DTOs only)
class StudentOption(ApiModel):
    label: Literal["A", "B", "C", "D"]
    text: str


class StudentContentBlock(ApiModel):
    id: UUID
    kind: Literal["heading", "paragraph", "data_fact", "instruction", "card_front", "card_back"]
    position: int
    payload: HeadingPayload | ParagraphPayload | InstructionPayload | DataFactPayload | CardPayload


class AttemptResult(ApiModel):
    item_id: UUID
    is_correct: bool | None = Field(None, description="null for SHORT / rubric items.")
    explanation: str | None = Field(None, description="Approved explanation; only present after the attempt.")
    model_config = ex({"itemId": I["q1"], "isCorrect": True,
                       "explanation": "Đồng bằng sông Hồng có số dân cao nhất (23,2 triệu người)."})


class StudentItem(ApiModel):
    id: UUID
    position: int
    item_type: ItemType
    skill: Skill
    stem: str
    options: list[StudentOption] = []
    result: AttemptResult | None = Field(None, description="Present only after this student answered.")


class StudentAssignmentOut(ApiModel):
    id: UUID
    title: str
    open_at: datetime
    due_at: datetime
    blocks: list[StudentContentBlock]
    items: list[StudentItem]
    model_config = ex({
        "id": I["assign"], "title": "Phân bố dân cư theo vùng", "openAt": T1, "dueAt": "2026-11-30T23:59:00+07:00",
        "blocks": [{"id": I["p1"], "kind": "paragraph", "position": 2,
                    "payload": {"text": "Dân cư nước ta phân bố không đều giữa các vùng kinh tế."}}],
        "items": [{"id": I["q1"], "position": 6, "itemType": "MCQ", "skill": "COMPARE",
                   "stem": "Theo bảng số liệu, vùng nào có số dân cao nhất?",
                   "options": [{"label": "A", "text": "Đồng bằng sông Hồng"}], "result": None}]})


class StudentAssignmentSummary(ApiModel):
    id: UUID
    title: str
    class_code: str
    class_name: str | None = Field(None, description="Class display name, e.g. 10A1 (falls back to the code).")
    open_at: datetime
    due_at: datetime
    status: Literal["NOT_STARTED", "IN_PROGRESS", "DONE", "CLOSED"]
    answered_count: int
    item_count: int
    model_config = ex({"id": I["assign"], "title": "Phân bố dân cư theo vùng", "classCode": "10A1", "className": "10A1",
                       "openAt": T1, "dueAt": "2026-11-30T23:59:00+07:00", "status": "NOT_STARTED", "answeredCount": 0,
                       "itemCount": 2})


class StudentAssignmentList(Page):
    items: list[StudentAssignmentSummary]
    model_config = ex({"items": [e0(StudentAssignmentSummary)], "nextCursor": None})


class AnswerIn(ApiModel):
    choice: Literal["A", "B", "C", "D"] | None = None
    value: float | None = None
    text: str | None = Field(None, max_length=2000)


class AttemptRequest(ApiModel):
    item_id: UUID
    answer: AnswerIn
    request_id: UUID = Field(description="Idempotency key (retry of the same submit). One attempt per item.")
    model_config = ex({"itemId": I["q1"], "answer": {"choice": "A"}, "requestId": I["request"]})


# ---------------------------------------------------------------- Habit (CHAT_ENABLED)
HabitAction = Literal["hint", "ask", "explain"]
QuickId = Literal["start", "where_data", "formula", "teacher"]


class ChatRequest(ApiModel):
    item_id: UUID = Field(description="The item the student is working on (must belong to this assignment).")
    action: HabitAction
    message: str | None = Field(None, max_length=300, description="Free question for `ask` (PII redacted before storing).")
    quick: QuickId | None = Field(None, description="Suggestion button instead of free text (with `ask`).")
    request_id: UUID = Field(description="Idempotency key: a retry returns the stored reply, uncounted.")
    model_config = ex({"itemId": I["q1"], "action": "hint", "requestId": I["request"]})


class SourceRef(ApiModel):
    block_id: UUID
    label: str = Field(description="Kind of approved block: Tiêu đề, Đoạn văn, Câu dẫn.")
    excerpt: str = Field(description="Approved text, verbatim from the published snapshot.")


class QuickAction(ApiModel):
    id: QuickId
    label: str


class ChatReply(ApiModel):
    reply: str = Field(description="Plain text. Never contains the answer before the student has answered the item.")
    hint_level: int = Field(description="1..3 for `hint`, 0 otherwise.")
    source_refs: list[SourceRef]
    extra: str | None = Field(None, description="Second part (CHAT_AI_EXTRA): general knowledge, NOT verified by the teacher.")
    suggestions: list[QuickAction] = Field(default_factory=list, description="Buttons offered after a refusal or off-topic.")
    blocked_reason: str | None = Field(None, description="Refusal code (e.g. ANSWER_REQUEST) when the reply is a refusal.")
    model_config = ex({"reply": "Em đọc kỹ đề và xác định đề đang hỏi về vùng nào, năm nào nhé.", "hintLevel": 1,
                       "sourceRefs": [], "blockedReason": None})


class HabitBadge(ApiModel):
    code: str = Field(description="TU_LUC, KIEN_TRI or THAM_HIEM.")
    label: str


class HabitItem(ApiModel):
    item_id: UUID
    hints_used: int
    hints_max: int
    advice: Literal["REVIEW", "QUIET"] | None = Field(
        None, description="From the student's own first-attempt results and hint use per skill (rules): REVIEW = suggest "
        "re-reading the lesson first; QUIET = the skill goes well, fewer nudges. Null when personalization is off.")
    preview: str | None = Field(None, description="Hint 1 text shown open for a REVIEW item (does not count as a hint used).")


class HabitOut(ApiModel):
    streak: int = Field(description="Consecutive days (Asia/Ho_Chi_Minh) with at least one answered item.")
    today_goal: int
    today_done: int
    badges: list[HabitBadge]
    hints_available: list[HabitItem]
    model_config = ex({"streak": 2, "todayGoal": 3, "todayDone": 1, "badges": [{"code": "TU_LUC", "label": "Tự lực"}],
                       "hintsAvailable": [{"itemId": I["q1"], "hintsUsed": 1, "hintsMax": 3}]})


# ---------------------------------------------------------------- Personalization (PERSONALIZATION_ENABLED)
PreferenceKey = Literal["chia_nho_tung_buoc", "hen_gio_tap_trung", "uu_tien_bang_so_lieu", "uu_tien_giai_thich", "nhac_tien_do",
                        "focus_mode_used"]


class PreferencesOut(ApiModel):
    preferences: dict[str, str] = Field(description="Only the options that are ON: `on`, or `5`/`10` minutes for "
                                        "`hen_gio_tap_trung`. A missing key means off.")
    model_config = ex({"preferences": {"chia_nho_tung_buoc": "on", "hen_gio_tap_trung": "10"}})


class PreferencesIn(ApiModel):
    preferences: dict[PreferenceKey, Literal["on", "off", "5", "10"]] = Field(
        description="Partial update: `off` removes the option. `hen_gio_tap_trung` takes `5`, `10` or `off`; others `on`/`off`.")
    model_config = ex({"preferences": {"chia_nho_tung_buoc": "on", "hen_gio_tap_trung": "off"}})


# ---------------------------------------------------------------- teacher insights (class teacher only, anonymous)
class InsightItem(ApiModel):
    item_block_id: UUID
    position: int
    stem: str
    skill: Skill
    answered_count: int
    first_attempt_correct_rate: float | None = Field(None, description="0..1; null when nobody answered.")
    hints_used: int = Field(description="HABIT AI hints asked for this item, all students together.")
    asks: int = Field(description="Questions typed or tapped in HABIT AI for this item, all students together.")


class InsightTheme(ApiModel):
    key: str = Field(description="answer, start, data, formula, unit, concept, compare or other.")
    label: str
    count: int
    examples: list[str] = Field(description="Up to 3 most repeated questions (personal data already removed).")


class InsightsOut(ApiModel):
    assignment_id: UUID
    lesson_id: UUID
    published_revision_id: UUID = Field(description="Revision this assignment was published from.")
    can_practice: bool = Field(description="True when the caller wrote the lesson, so extra practice can be drafted from it.")
    student_count: int
    asking_students: int = Field(description="How many different students asked something (never who).")
    total_questions: int
    items: list[InsightItem]
    themes: list[InsightTheme]
    focus_skills: list[Skill] = Field(description="Skills of the items with the lowest first-attempt correct rate (up to 2).")
    llm_available: bool
    model_config = ex({"assignmentId": I["assign"], "lessonId": I["lesson"], "publishedRevisionId": I["lrev"],
                       "canPractice": True, "studentCount": 15, "askingStudents": 6, "totalQuestions": 14, "items": [],
                       "focusSkills": ["COMPARE"],
                       "themes": [{"key": "start", "label": "Chưa biết bắt đầu từ đâu", "count": 5,
                                   "examples": ["Em nên bắt đầu từ đâu?"]}], "llmAvailable": False})


class AnalyzeOut(ApiModel):
    topics: list[str] = Field(description="3 to 5 short topics students get stuck on (empty when there is no data).")
    generated_by: Literal["rule", "llm"]
    model_config = ex({"topics": ["Chưa biết bắt đầu từ đâu: 5 lượt hỏi"], "generatedBy": "rule"})


# ---------------------------------------------------------------- lesson plans (CV 5512), teacher only
class PlanMcqOption(ApiModel):
    label: Literal["A", "B", "C", "D"]
    text: str


class PlanMcq(ApiModel):
    id: UUID
    position: int
    stem: str
    options: list[PlanMcqOption]
    correct_option: Literal["A", "B", "C", "D"] | None
    answer_source: Literal["underline", "docx_underline", "teacher"] | None
    needs_confirmation: bool


class PlanItem(ApiModel):
    anchor_id: UUID
    page: int | None
    type: str = Field(description="paragraph, heading, knowledge_box, table_cell or figure_caption.")
    text: str


class PlanSection(ApiModel):
    kind: str
    activity_type: Literal["mo_dau", "hinh_thanh", "luyen_tap", "van_dung"] | None
    sub: str | None
    items: list[PlanItem]


class PlanObjective(ApiModel):
    text: str
    competency_code: str | None
    competency_name: str | None


class PlanOut(ApiModel):
    id: UUID
    title: str
    subject: str
    grade: int | None
    ppct_period: str | None
    week: str | None
    taught_from: date | None
    taught_to: date | None
    suggested_due_at: datetime | None = Field(description="Day before the first teaching day, 23:59 (UTC+7).")
    redacted_count: int
    activities: list[str]
    mcq_count: int
    needs_confirmation_count: int
    lesson_id: UUID | None = Field(description="Set once 'Tạo bài chuẩn bị' has been used.")


class PlanDetail(PlanOut):
    sections: list[PlanSection]
    objectives: list[PlanObjective]
    mcqs: list[PlanMcq]


class PlanList(ApiModel):
    items: list[PlanOut]


class PlanMcqAnswer(ApiModel):
    correct_option: Literal["A", "B", "C", "D"]


class PlanLessonOut(ApiModel):
    lesson_id: UUID
    blocks: int
    practice_items: int
    skipped_unconfirmed: int = Field(description="MCQ left out because the teacher has not confirmed the answer.")
    left_for_after_class: int = Field(description="Confirmed MCQ beyond the first 5 (not turned into blocks yet).")
