"""VAL-11: an item whose explanation uses data the student never saw (reviewer report: 4 regions, stem shows 2)."""
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.validation import Ctx, val11
from app.validation.leak import visible_text

REGIONS = {"ĐBSH": "23,2", "TD&MNPB": "12,6", "Tây Nguyên": "5,9", "ĐNB": "17,8"}
SOURCE = [Decimal("23.2"), Decimal("12.6"), Decimal("5.9"), Decimal("17.8")]


def _b(kind: str, payload: dict[str, Any], parent: Any = None) -> Any:
    return SimpleNamespace(id=uuid4(), kind=kind, payload=payload, parent_id=parent)


def _run(shown_regions: list[str]) -> Any:
    facts = [_b("data_fact", {"label": r, "value": float(REGIONS[r].replace(",", ".")), "unit": "%"}) for r in shown_regions]
    item = _b("worksheet_item", {"stem": "Vùng nào có tỉ lệ cao nhất?", "itemType": "MCQ", "skill": "COMPARE"})
    kids = [_b("option", {"label": "ABCD"[i], "text": r}, item.id) for i, r in enumerate(REGIONS)]
    kids += [_b("answer_key", {"correct": "A"}, item.id),
             _b("explanation", {"text": "; ".join(f"{r} {v}%" for r, v in REGIONS.items())}, item.id)]
    blocks = [*facts, item]
    visible = [(b.id, "stem" if b.kind == "worksheet_item" else b.kind, visible_text(b.kind, b.payload)) for b in blocks]
    ctx = Ctx(anchors={}, lesson_numbers=set(SOURCE), links={}, children={item.id: kids}, last_approval={},
              source_hashes={}, visible=visible)
    return val11(item, ctx)


def test_item_missing_two_regions_of_data_is_a_blocker() -> None:
    r = _run(["ĐBSH", "TD&MNPB"])
    assert r.outcome == "FAIL" and r.severity == "BLOCKER"
    assert r.evidence["numbersNotShown"] == [5.9, 17.8]


def test_item_with_all_regions_shown_passes() -> None:
    assert _run(list(REGIONS)).outcome == "PASS"
