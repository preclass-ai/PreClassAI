"""Validation rules VAL-01..10 and the runner (GĐ7; VAL-10 = no answer leak before submitting, see leak.py).

Results are append-only and bound to the block's content_hash. The runner never approves anything: it only moves a
block between UNREVIEWED / AUTO_CHECKED / FLAGGED, and APPROVED -> REVIEW_AGAIN when an approval is no longer valid.
VAL-07 (images) is a stub that passes and writes no rows. shortcut: VAL-08 uses a short glossary file; extend it with
the Geography team's list.
"""

import unicodedata
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m
from app.hashing import norm_text
from app.schemas import BlockValidationSummary, ValidateOut
from app.sources.numbers import parse_numbers
from app.validation.leak import item_answer_leaks, severity, visible_text

_GLOSSARY = [t.strip().lower() for t in (Path(__file__).parent / "glossary_geo.txt").read_text(encoding="utf-8").splitlines()
             if t.strip() and not t.startswith("#")]
_TEXT_KEYS = ("text", "stem", "note", "label", "region", "unit", "period")
TOL = Decimal("0.05")


@dataclass
class R:
    rule: str
    severity: str
    outcome: str
    evidence: dict[str, Any] = field(default_factory=dict)


def _fail(rule: str, severity: str, **ev: Any) -> R:
    return R(rule, severity, "FAIL", ev)


def _pass(rule: str, severity: str = "BLOCKER") -> R:
    return R(rule, severity, "PASS")


@dataclass
class Link:
    status: str
    relation: str
    code: str
    excerpt: str
    numbers: list[Decimal]
    in_lesson: bool
    asset_visibility: str
    asset_license: str | None


@dataclass
class Ctx:
    anchors: dict[str, list[Decimal]]  # lesson anchor code -> numbers
    lesson_numbers: set[Decimal]
    links: dict[UUID, list[Link]]
    children: dict[UUID, list[m.ContentBlock]]
    last_approval: dict[UUID, m.ReviewEvent]
    source_hashes: dict[UUID, list[str]]
    visible: list[tuple[UUID, str, str]] = field(default_factory=list)  # (block id, kind, text) a student sees before answering


def _exempt(n: Decimal) -> bool:  # years and small ordinals (PR-07)
    return n == n.to_integral_value() and (Decimal(1900) <= n <= Decimal(2100) or Decimal(0) <= n <= Decimal(10))


def payload_numbers(payload: dict[str, Any]) -> list[Decimal]:
    out: list[Decimal] = []
    for k, v in payload.items():
        if k in ("tolerance", "derivation"):
            continue
        if isinstance(v, bool):
            continue
        if isinstance(v, (int, float)):
            out.append(Decimal(str(v)))
        elif isinstance(v, str) and (k in _TEXT_KEYS or k == "correct"):
            out += parse_numbers(v)
        elif isinstance(v, list):
            for s in v:
                if isinstance(s, str):
                    out += parse_numbers(s)
    return out


def derive(d: dict[str, Any], anchors: dict[str, list[Decimal]]) -> Decimal | None:
    """Recompute a derivation with Decimal; None when an operand is unknown or the op is invalid."""
    vals: list[Decimal] = []
    for o in d.get("operands", []):
        if isinstance(o, str):
            nums = anchors.get(o)
            if not nums:
                return None
            vals.append(nums[0])
        else:
            vals.append(Decimal(str(o)))
    if len(vals) < 2:
        return None
    try:
        op = d.get("op")
        if op == "sum":
            return sum(vals, Decimal(0))
        if op == "diff":
            return vals[0] - sum(vals[1:], Decimal(0))
        if op == "ratio":
            return vals[0] / vals[1]
        if op == "percent":
            return vals[0] / vals[1] * 100
    except (InvalidOperation, ZeroDivisionError):
        return None
    return None


def _first_diff(a: str, b: str) -> int:
    for i, (x, y) in enumerate(zip(a, b, strict=False)):
        if x != y:
            return i
    return min(len(a), len(b))


def val01(b: m.ContentBlock, ctx: Ctx) -> R | None:
    links = ctx.links.get(b.id, [])
    if not links:
        return None
    bad = [lk.code for lk in links if lk.status != "VERIFIED" or not lk.in_lesson]
    return _fail("VAL-01", "BLOCKER", badAnchors=bad) if bad else _pass("VAL-01")


def val02(b: m.ContentBlock, ctx: Ctx) -> R | None:
    if b.transformation != "ORIGINAL" or not isinstance(b.payload.get("text"), str):
        return None
    text = norm_text(b.payload["text"])
    good = [lk for lk in ctx.links.get(b.id, []) if lk.status == "VERIFIED"]
    if not good:
        return _fail("VAL-02", "BLOCKER", reason="no_anchor")
    if any(text in norm_text(lk.excerpt) for lk in good):  # exact, diacritics preserved
        return _pass("VAL-02")
    best = max(good, key=lambda lk: sum(1 for x, y in zip(text, norm_text(lk.excerpt), strict=False) if x == y))
    return _fail("VAL-02", "BLOCKER", anchor=best.code, position=_first_diff(text, norm_text(best.excerpt)))


def val03(b: m.ContentBlock, ctx: Ctx) -> R | None:
    verified = [lk for lk in ctx.links.get(b.id, []) if lk.status == "VERIFIED"]
    needs_source = b.is_factual or b.transformation == "AI_PROPOSED"
    problems: dict[str, Any] = {}
    if needs_source and not verified and not (b.no_source_reason or "").strip():
        problems["reason"] = "no_verified_source_and_no_reason"
    allowed = {n for lk in verified for n in lk.numbers} if verified else ctx.lesson_numbers
    derivation = b.payload.get("derivation")
    result = derive(derivation, ctx.anchors) if isinstance(derivation, dict) else None
    if isinstance(derivation, dict) and result is None:
        problems["derivation"] = "unresolvable"
    extra = []
    for n in payload_numbers(b.payload):
        if n in allowed or _exempt(n):
            continue
        if result is not None and abs(n - result) <= max(TOL, Decimal(str(b.payload.get("tolerance") or 0))):
            continue
        extra.append(float(n))
    if extra:
        problems["numbersNotInSources"] = extra
    if not (b.is_factual or b.transformation == "AI_PROPOSED" or verified or extra):
        return None
    return _fail("VAL-03", "BLOCKER", **problems) if problems else _pass("VAL-03")


def val04(b: m.ContentBlock, ctx: Ctx) -> R | None:
    if b.kind != "worksheet_item":
        return None
    kids = ctx.children.get(b.id, [])
    keys = [k for k in kids if k.kind == "answer_key"]
    opts = [k for k in kids if k.kind == "option"]
    itype = b.payload.get("itemType")
    if len(keys) != 1:
        return _fail("VAL-04", "BLOCKER", reason="answer_keys", count=len(keys))
    key = keys[0].payload
    if itype == "MCQ":
        labels = {o.payload.get("label") for o in opts}
        if key.get("correct") not in labels:
            return _fail("VAL-04", "BLOCKER", reason="correct_option_missing")
    elif itype == "NUMERIC":
        if "value" not in key or not str(key.get("unit") or "").strip():
            return _fail("VAL-04", "BLOCKER", reason="numeric_needs_value_and_unit")
    return _pass("VAL-04")


def val05(b: m.ContentBlock, ctx: Ctx) -> R | None:
    if b.kind != "worksheet_item" or b.payload.get("itemType") != "MCQ":
        return None
    labels = [str(o.payload.get("label")) for o in ctx.children.get(b.id, []) if o.kind == "option"]
    keys = [k for k in ctx.children.get(b.id, []) if k.kind == "answer_key"]
    if keys and keys[0].payload.get("correct") not in labels:
        return _fail("VAL-05", "BLOCKER", reason="correct_option_missing")
    if len(set(labels)) != len(labels) or sorted(labels) != list("ABCD")[: len(labels)]:
        return _fail("VAL-05", "WARNING", labels=labels)
    return _pass("VAL-05", "WARNING")


def val06(b: m.ContentBlock, ctx: Ctx) -> R | None:
    if b.review_status != "APPROVED":
        return None
    ev = ctx.last_approval.get(b.id)
    ok = ev is not None and ev.action == "APPROVE" and ev.content_hash == b.content_hash \
        and sorted(ev.source_hashes) == ctx.source_hashes.get(b.id, [])
    return _pass("VAL-06") if ok else _fail("VAL-06", "BLOCKER", reason="approval_no_longer_matches")


def val08(b: m.ContentBlock, ctx: Ctx) -> R | None:
    text = unicodedata.normalize("NFC", " ".join(str(b.payload.get(k, "")) for k in _TEXT_KEYS)).lower()
    hits = [t for t in _GLOSSARY if t in text]
    return _fail("VAL-08", "WARNING", terms=hits) if hits else None


def val09(b: m.ContentBlock, ctx: Ctx) -> R | None:
    links = ctx.links.get(b.id, [])
    if not links:
        return None
    bad = [lk.code for lk in links if lk.asset_visibility == "SCHOOL" and not (lk.asset_license or "").strip()]
    return _fail("VAL-09", "BLOCKER", anchors=bad) if bad else _pass("VAL-09")


def val10(b: m.ContentBlock, ctx: Ctx) -> R | None:
    """The answer must not be readable from anything shown before this item is answered (every subject)."""
    if b.kind != "worksheet_item":
        return None
    kids = ctx.children.get(b.id, [])
    key = next((k.payload for k in kids if k.kind == "answer_key"), {})
    opts = sorted((str(o.payload.get("label")), str(o.payload.get("text"))) for o in kids if o.kind == "option")
    found = item_answer_leaks(str(b.payload.get("itemType")), opts, key,
                              [(str(i), k, t) for i, k, t in ctx.visible if i != b.id])
    if not found:
        return _pass("VAL-10")
    return _fail("VAL-10", severity(found), findings=found)


RULES = (val01, val02, val03, val04, val05, val06, val08, val09, val10)  # VAL-07 (images): P1 stub, always passes


async def _context(db: AsyncSession, revision_id: UUID, blocks: list[m.ContentBlock]) -> Ctx:
    src_ids = list(await db.scalars(select(m.LessonSource.source_revision_id).where(
        m.LessonSource.lesson_revision_id == revision_id)))
    anchors = {a.code: list(a.numbers) for a in await db.scalars(select(m.SourceAnchor).where(
        m.SourceAnchor.source_revision_id.in_(src_ids)))} if src_ids else {}
    ids = [b.id for b in blocks]
    links: dict[UUID, list[Link]] = {}
    shash: dict[UUID, set[str]] = {}
    if ids:
        rows = (await db.execute(
            select(m.ProvenanceLink, m.SourceAnchor, m.SourceRevision, m.SourceAsset)
            .join(m.SourceAnchor, m.SourceAnchor.id == m.ProvenanceLink.anchor_id)
            .join(m.SourceRevision, m.SourceRevision.id == m.SourceAnchor.source_revision_id)
            .join(m.SourceAsset, m.SourceAsset.id == m.SourceRevision.asset_id)
            .where(m.ProvenanceLink.block_id.in_(ids)))).all()
        for lk, a, sr, asset in rows:
            links.setdefault(lk.block_id, []).append(Link(
                lk.status, lk.relation, a.code, a.excerpt, list(a.numbers), a.source_revision_id in set(src_ids),
                asset.visibility, asset.license_note))
            if lk.status == "VERIFIED":
                shash.setdefault(lk.block_id, set()).update({sr.sha256, a.excerpt_hash})
    children: dict[UUID, list[m.ContentBlock]] = {}
    for b in blocks:
        if b.parent_id:
            children.setdefault(b.parent_id, []).append(b)
    approved = [b.id for b in blocks if b.review_status == "APPROVED"]
    last: dict[UUID, m.ReviewEvent] = {}
    if approved:
        for ev in await db.scalars(select(m.ReviewEvent).where(m.ReviewEvent.block_id.in_(approved)).order_by(
                m.ReviewEvent.created_at)):
            last[ev.block_id] = ev
    visible = [(b.id, "stem" if b.kind == "worksheet_item" else b.kind, visible_text(b.kind, b.payload)) for b in blocks
               if b.kind in ("heading", "paragraph", "instruction", "data_fact", "card_front", "worksheet_item")]
    return Ctx(anchors, {n for ns in anchors.values() for n in ns}, links, children, last,
               {k: sorted(v) for k, v in shash.items()}, visible)


async def evaluate_revision(db: AsyncSession, revision_id: UUID) -> tuple[list[m.ContentBlock], dict[UUID, list[R]]]:
    """Fresh, read-only evaluation of every rule on every block (nothing is written)."""
    blocks = list((await db.scalars(select(m.ContentBlock).where(
        m.ContentBlock.revision_id == revision_id, m.ContentBlock.deleted_at.is_(None))
        .order_by(m.ContentBlock.position))).all())
    ctx = await _context(db, revision_id, blocks)
    return blocks, {b.id: [r for rule in RULES if (r := rule(b, ctx)) is not None] for b in blocks}


async def validate_revision(db: AsyncSession, revision_id: UUID) -> ValidateOut:
    blocks, evaluated = await evaluate_revision(db, revision_id)
    prev: dict[tuple[UUID, str], tuple[str, str]] = {}  # latest stored (hash, outcome) per block+rule
    if blocks:
        for bid, rule, h, outcome in (await db.execute(
            select(m.ValidationResult.block_id, m.ValidationResult.rule, m.ValidationResult.content_hash,
                   m.ValidationResult.outcome).where(m.ValidationResult.block_id.in_([b.id for b in blocks]))
                .order_by(m.ValidationResult.created_at))).all():
            prev[(bid, rule)] = (h, outcome)
    new_rows: list[dict[str, Any]] = []
    summaries: list[BlockValidationSummary] = []
    blockers = warnings = 0
    for b in blocks:
        results = evaluated[b.id]
        for r in results:
            if prev.get((b.id, r.rule)) != (b.content_hash, r.outcome):
                new_rows.append({"block_id": b.id, "rule": r.rule, "severity": r.severity, "outcome": r.outcome,
                                 "evidence": r.evidence, "method": "rule", "content_hash": b.content_hash})
        failed = [r for r in results if r.outcome == "FAIL"]
        has_blocker = any(r.severity == "BLOCKER" for r in failed)
        blockers += sum(1 for r in failed if r.severity == "BLOCKER")
        warnings += sum(1 for r in failed if r.severity == "WARNING")
        if b.review_status == "APPROVED" and has_blocker:
            new_status = "REVIEW_AGAIN"
        elif b.review_status in ("UNREVIEWED", "AUTO_CHECKED", "FLAGGED"):
            new_status = "FLAGGED" if has_blocker else "AUTO_CHECKED"
        else:
            new_status = b.review_status
        if new_status != b.review_status:
            await db.execute(update(m.ContentBlock).where(m.ContentBlock.id == b.id).values(review_status=new_status))
        if failed:
            summaries.append(BlockValidationSummary(block_id=b.id, review_status=new_status,
                                                    failed_rules=[r.rule for r in failed]))
    if new_rows:
        await db.execute(insert(m.ValidationResult), new_rows)
    await db.commit()
    return ValidateOut(revision_id=revision_id, blocker_count=blockers, warning_count=warnings, blocks=summaries)
