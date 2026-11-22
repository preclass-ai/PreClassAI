"""Seed mock data (all fictional, labelled in the teacher-only source note). Run after migrations:

    DATABASE_URL=... uv run python -m seed.seed

Refuses to run when APP_ENV=production. Re-running is a no-op once seeded. Passwords: see seed/passwords.py (dev: $SEED_PASSWORD; APP_ENV=demo: per-role SEED_*_PASSWORD, required)
(default "preclass-demo", DEV ONLY; set your own anywhere else).
"""

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import insert, select, update
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

from app.config import get_settings
from app.db import models as m
from app.hashing import content_hash, excerpt_hash, sha256_hex, source_hashes
from app.ids import uid
from app.snapshot import build_snapshot
from app.sources.numbers import parse_numbers
from seed.lessons import LESSONS, NOTE
from seed.passwords import MissingSeedPassword
from seed.passwords import hashes as pw_hashes

DOMAIN = "preclass.local"


def vn(d: Decimal) -> str:
    """Vietnamese number format: '.' thousands, ',' decimal."""
    return f"{d:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass
class Blk:
    key: str
    kind: str
    parent: str | None
    payload: dict[str, Any]
    transformation: str
    factual: bool = False
    reason: str | None = None
    links: list[tuple[str, str]] = field(default_factory=list)  # (anchor name, relation)
    deps: list[tuple[str, str]] = field(default_factory=list)  # (depends_on key, kind)


AI_REASON = "Nội dung sư phạm do AI đề xuất, không lấy trực tiếp từ nguồn."


def build_blocks(spec: dict[str, Any], vals: list[Decimal], code: dict[str, str], *, extra: str) -> list[Blk]:
    rows = spec["rows"]
    labels = [r[0] for r in rows]
    unit, metric = spec["unit"], spec["metric"]
    order = sorted(range(len(vals)), key=lambda i: vals[i], reverse=True)
    imax, isec, imin = order[0], order[1], order[-1]
    cell = lambda i: f"r{i + 1}c1"  # noqa: E731
    diff = vals[imax] - vals[imin]
    deriv = {"op": "diff", "operands": [code[cell(imax)], code[cell(imin)]]}
    B = Blk
    out = [
        B("h", "heading", None, {"text": spec["heading"]}, "ORIGINAL", links=[("h", "quotes")]),
        B("p1", "paragraph", None, {"text": spec["paras"][0]}, "ORIGINAL", True, links=[("p1", "quotes")]),
        B("p2", "paragraph", None, {"text": spec["paras"][1]}, "ORIGINAL", True, links=[("p2", "quotes")]),
        B("ins", "instruction", None, {"text": "Đọc bảng số liệu và trả lời các câu hỏi sau."},
          "AI_PROPOSED", reason=AI_REASON),
    ]
    # The whole data table is shown (one fact per row) so the questions can be answered by reading it; showing only the
    # row that is the answer would give it away (VAL-10). Key "df" stays the first row.
    for i, lab in enumerate(labels):
        out.append(B("df" if i == 0 else f"df{i}", "data_fact", None,
                     {"label": f"{lab}: {metric}", "value": float(vals[i]), "unit": unit,
                      "period": spec["period"], "region": spec["area"] or lab},
                     "PARAPHRASED", True, links=[(f"r{i + 1}c0", "derived_from"), (cell(i), "derived_from")]))
    out += [
        B("p3", "paragraph", None, {"text": spec["paras"][2]}, "ORIGINAL", True, links=[("p3", "quotes")]),  # the one practice-data note
        B("q1", "worksheet_item", None,
          {"stem": f"Theo bảng số liệu, {spec['ent'].lower()} nào có {metric} cao nhất?",
           "itemType": "MCQ", "skill": "COMPARE"}, "AI_PROPOSED", reason=AI_REASON),
    ]
    for i, lab in enumerate(labels):
        out.append(B(f"q1o{i}", "option", "q1", {"label": "ABCD"[i], "text": lab}, "AI_PROPOSED",
                     reason=AI_REASON, deps=[("q1", "LABEL_OF")]))
    out += [
        B("q1k", "answer_key", "q1", {"correct": "ABCD"[imax]}, "SYNTHESISED", True,
          links=[(cell(i), "derived_from") for i in range(len(vals))], deps=[("q1", "ANSWER_OF")]),
        B("q1e", "explanation", "q1",
          {"text": f"{labels[imax]} có {metric} cao nhất ({vn(vals[imax])} {unit}), "
                   f"cao hơn {labels[isec]} ({vn(vals[isec])} {unit}).{extra}"},
          "SYNTHESISED", True, links=[(cell(imax), "supports"), (cell(isec), "supports")],
          deps=[("q1k", "EXPLANATION_OF")]),
        B("q2", "worksheet_item", None,
          {"stem": f"Tính chênh lệch {metric} giữa {spec['ent'].lower()} cao nhất và {spec['ent'].lower()} thấp nhất (đơn vị: {unit}).",
           "itemType": "NUMERIC", "skill": "CALCULATE"}, "AI_PROPOSED", reason=AI_REASON),
        B("q2k", "answer_key", "q2",
          {"value": float(diff), "unit": unit, "tolerance": 0.05, "derivation": deriv}, "SYNTHESISED", True,
          links=[(cell(imax), "derived_from"), (cell(imin), "derived_from")], deps=[("q2", "ANSWER_OF")]),
        B("q2e", "explanation", "q2",
          {"text": f"Chênh lệch = {vn(vals[imax])} − {vn(vals[imin])} = {vn(diff)} {unit}.",
           "derivation": deriv}, "SYNTHESISED", True,
          links=[(cell(imax), "supports"), (cell(imin), "supports")], deps=[("q2k", "EXPLANATION_OF")]),
    ]
    return out


def rules_for(b: Blk) -> list[str]:
    r = []
    if b.links:
        r.append("VAL-01")
    if b.transformation == "ORIGINAL":
        r.append("VAL-02")
    if b.factual:
        r.append("VAL-03")
    if b.kind == "worksheet_item":
        r.append("VAL-04")
        r.append("VAL-10")
    if b.kind == "option":
        r.append("VAL-05")
    return r


async def ins(conn: AsyncConnection, model: type[m.Base], rows: list[dict[str, Any]]) -> None:
    if rows:
        await conn.execute(insert(model.__table__), rows)  # type: ignore[attr-defined]


async def seed(conn: AsyncConnection, pw_by_role: dict[str, str]) -> None:
    now = datetime.now(UTC)
    # --- users and classes
    staff = [("gv.dia", "TEACHER", "Cô Địa Lí (minh họa)"), ("gv.khac", "TEACHER", "Thầy Khác (minh họa)"),
             ("reviewer", "REVIEWER", "Người duyệt (minh họa)"), ("admin", "ADMIN", "Quản trị (minh họa)")]
    users = [{"id": uid(f"user:{n}"), "email": f"{n}@{DOMAIN}", "login_code": None, "display_name": d,
              "role": r, "password_hash": pw_by_role[r]}
             for n, r, d in staff]
    classes = {"10A1": 10, "11A1": 11}
    members = []
    for code, grade in classes.items():
        members.append({"class_id": uid(f"class:{code}"), "user_id": uid("user:gv.dia"), "role_in_class": "TEACHER"})
        for i in range(1, 16):
            login = f"HS{grade}-{i:02d}"
            users.append({"id": uid(f"user:{login}"), "email": None, "login_code": login,
                          "display_name": f"Học sinh {grade}-{i:02d} (minh họa)", "role": "STUDENT",
                          "password_hash": pw_by_role["STUDENT"]})
            members.append({"class_id": uid(f"class:{code}"), "user_id": uid(f"user:{login}"),
                            "role_in_class": "STUDENT"})
    await ins(conn, m.AppUser, users)
    await ins(conn, m.Class, [{"id": uid(f"class:{c}"), "code": c, "grade": g, "name": c} for c, g in classes.items()])
    await ins(conn, m.ClassMember, members)

    for li, spec in enumerate(LESSONS):
        key, author = spec["key"], uid(f"user:{spec['author']}")
        asset, rev = uid(f"{key}:asset"), uid(f"{key}:srcrev")
        lesson, lrev = uid(f"{key}:lesson"), uid(f"{key}:lrev")
        # --- source text + anchors (heading, 2 paragraphs, 5x2 table cells)
        cells: dict[str, tuple[str, str, dict[str, Any]]] = {
            "h": ("HEADING", spec["heading"], {"para_index": 0}),
            "p1": ("PARAGRAPH", spec["paras"][0], {"para_index": 1}),
            "p2": ("PARAGRAPH", spec["paras"][1], {"para_index": 2}),
            "p3": ("PARAGRAPH", spec["paras"][2], {"para_index": 3}),
            "r0c0": ("TABLE_CELL", spec["ent"], {"table": 0, "row": 0, "col": 0}),
            "r0c1": ("TABLE_CELL", f"Giá trị ({spec['unit']})", {"table": 0, "row": 0, "col": 1}),
        }
        for i, (lab, val) in enumerate(spec["rows"], start=1):
            cells[f"r{i}c0"] = ("TABLE_CELL", lab, {"table": 0, "row": i, "col": 0})
            cells[f"r{i}c1"] = ("TABLE_CELL", val, {"table": 0, "row": i, "col": 1})
        code = {n: f"anc_{str(rev)[:8]}_{seq:03d}" for seq, n in enumerate(cells, start=1)}
        anchors = {n: {"id": uid(f"{key}:anchor:{n}"), "source_revision_id": rev, "code": code[n], "kind": k,
                       "locator": loc, "excerpt": ex, "excerpt_hash": excerpt_hash(ex),
                       "numbers": parse_numbers(ex)} for n, (k, ex, loc) in cells.items()}
        text = "\n".join(c[1] for c in cells.values())
        await ins(conn, m.SourceAsset, [{"id": asset, "owner_id": author, "title": f"{spec['title']} ({spec['key']})",
                                         "license_note": f"{NOTE}, không phải số liệu chính thức.",
                                         "visibility": spec["visibility"]}])
        src_sha = sha256_hex(text)
        await ins(conn, m.SourceRevision, [{"id": rev, "asset_id": asset, "version": 1, "sha256": src_sha,
                                            "mime": "text/plain", "extract_status": "OK", "locked_at": now}])
        await ins(conn, m.SourceAnchor, list(anchors.values()))
        await ins(conn, m.Lesson, [{"id": lesson, "author_id": author, "grade": spec["grade"],
                                    "title": spec["title"], "goal": spec["goal"]}])
        await ins(conn, m.LessonRevision, [{"id": lrev, "lesson_id": lesson, "revision_no": 1, "state": "DRAFT"}])
        await ins(conn, m.LessonSource, [{"lesson_revision_id": lrev, "source_revision_id": rev}])

        # --- blocks (lesson 2 gets an AI-added number absent from the source: seeded as FLAGGED)
        vals = [parse_numbers(r[1])[0] for r in spec["rows"]]
        extra = " Gấp khoảng 5,5 lần nhóm thấp nhất." if li == 1 else ""
        blks = build_blocks(spec, vals, code, extra=extra)
        bid = lambda k: uid(f"{key}:blk:{k}")  # noqa: E731
        hashes = {b.key: content_hash(b.kind, b.payload, str(bid(b.parent)) if b.parent else None,
                                      b.transformation, b.reason) for b in blks}
        await ins(conn, m.ContentBlock, [
            {"id": bid(b.key), "revision_id": lrev, "kind": b.kind, "parent_id": bid(b.parent) if b.parent else None,
             "position": pos, "payload": b.payload, "content_hash": hashes[b.key], "transformation": b.transformation,
             "no_source_reason": b.reason, "is_factual": b.factual} for pos, b in enumerate(blks, start=1)])
        await ins(conn, m.ProvenanceLink, [
            {"block_id": bid(b.key), "anchor_id": anchors[a]["id"], "relation": rel,
             "rationale": "Dữ liệu minh họa" if rel != "quotes" else None} for b in blks for a, rel in b.links])
        await ins(conn, m.BlockDependency, [
            {"block_id": bid(b.key), "depends_on_block_id": bid(d), "kind": k} for b in blks for d, k in b.deps])
        await ins(conn, m.TransformationEvent, [
            {"block_id": bid(b.key), "actor_type": "AI", "operation": "GENERATE", "after_hash": hashes[b.key],
             "generator_version": "mock-v1"} for b in blks])

        # --- target review states
        state = {b.key: "AUTO_CHECKED" for b in blks}
        if li == 0:
            state = {k: "APPROVED" for k in state}
        elif li == 1:
            state.update({"h": "APPROVED", "p1": "REVIEW_AGAIN", "ins": "UNREVIEWED", "q1e": "FLAGGED",
                          "q2k": "REJECTED"})
        byk = {b.key: b for b in blks}

        def vrows(b: Blk, h: str, st: str) -> list[dict[str, Any]]:
            fail = st == "FLAGGED"
            return [{"block_id": bid(b.key), "rule": r, "severity": "BLOCKER",
                     "outcome": "FAIL" if fail and r == "VAL-03" else "PASS",
                     "evidence": {"numbersNotInAnchors": [5.5]} if fail and r == "VAL-03" else {},
                     "method": "rule", "content_hash": h} for r in rules_for(b)]

        await ins(conn, m.ValidationResult,
                  [r for b in blks if state[b.key] != "UNREVIEWED" for r in vrows(b, hashes[b.key], state[b.key])])

        def shashes(b: Blk) -> list[str]:
            return source_hashes([src_sha] if b.links else [], [anchors[a]["excerpt_hash"] for a, _ in b.links])

        reviewer = author
        approve = [k for k, s in state.items() if s in ("APPROVED", "REVIEW_AGAIN")]
        await ins(conn, m.ReviewEvent, [
            {"block_id": bid(k), "content_hash": hashes[k], "source_hashes": shashes(byk[k]), "reviewer_id": reviewer,
             "action": "APPROVE", "note": None} for k in approve])
        if "q2k" in state and state["q2k"] == "REJECTED":
            await ins(conn, m.ReviewEvent, [{"block_id": bid("q2k"), "content_hash": hashes["q2k"],
                                             "source_hashes": shashes(byk["q2k"]), "reviewer_id": reviewer,
                                             "action": "REJECT", "note": "Cần ghi rõ đơn vị trong đáp án."}])
        for k, st in state.items():
            if st not in ("UNREVIEWED", "REVIEW_AGAIN"):  # REVIEW_AGAIN is set by the edit below
                await conn.execute(update(m.ContentBlock.__table__).where(
                    m.ContentBlock.__table__.c.id == bid(k)).values(review_status=st))
        if li == 1:  # teacher edited an approved paragraph -> new hash, approval no longer valid
            old = byk["p1"]
            new_payload = {"text": old.payload["text"].replace("quan trọng", "rất quan trọng")}
            new_hash = content_hash("paragraph", new_payload, None, "PARAPHRASED", None)
            await conn.execute(update(m.ContentBlock.__table__).where(
                m.ContentBlock.__table__.c.id == bid("p1")).values(
                payload=new_payload, transformation="PARAPHRASED", content_hash=new_hash, version=2,
                review_status="REVIEW_AGAIN"))
            await ins(conn, m.TransformationEvent, [{"block_id": bid("p1"), "actor_type": "TEACHER",
                                                     "actor_id": author, "operation": "EDIT",
                                                     "before_hash": hashes["p1"], "after_hash": new_hash}])
            await ins(conn, m.ValidationResult, [{"block_id": bid("p1"), "rule": r, "severity": "BLOCKER",
                                                  "outcome": "PASS", "evidence": {}, "method": "rule",
                                                  "content_hash": new_hash} for r in ("VAL-01", "VAL-03")])

        # --- publish lesson 1 and assign it to class 10A1
        if spec["publish"]:
            snap, snap_hash = build_snapshot(spec["title"], spec["grade"], [
                {"id": bid(b.key), "kind": b.kind, "parent_id": bid(b.parent) if b.parent else None,
                 "position": pos, "payload": b.payload} for pos, b in enumerate(blks, start=1)])
            pv = uid(f"{key}:published")
            await ins(conn, m.PublishedVersion, [{"id": pv, "lesson_revision_id": lrev, "snapshot": snap,
                                                  "snapshot_hash": snap_hash, "published_by": author}])
            await conn.execute(update(m.LessonRevision.__table__).where(
                m.LessonRevision.__table__.c.id == lrev).values(state="PUBLISHED"))
            await ins(conn, m.Assignment, [{"id": uid(f"{key}:assignment"), "published_version_id": pv,
                                            "class_id": uid("class:10A1"), "open_at": now - timedelta(days=1),
                                            "due_at": now + timedelta(days=30)}])


async def main() -> None:
    if get_settings().app_env.lower() in ("production", "prod"):
        raise SystemExit("Refusing to seed: APP_ENV=production (demo accounts share a known password).")
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        if (await conn.execute(select(m.AppUser.id).where(m.AppUser.email == f"gv.dia@{DOMAIN}"))).first():
            print("already seeded")
        else:
            try:
                hashed = pw_hashes(get_settings().app_env)
            except MissingSeedPassword as e:
                print(f"WARNING: demo accounts NOT created: {e}. The API starts anyway; set the variables and restart.")
            else:
                await seed(conn, hashed)
                print(f"seeded {len(LESSONS)} lessons; accounts: gv.dia@{DOMAIN}, HS10-01, HS11-01, admin@{DOMAIN}")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
