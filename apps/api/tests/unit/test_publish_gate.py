from types import SimpleNamespace
from typing import Any
from uuid import uuid4

from app.publish import _gate


def _block(kind: str) -> Any:
    return SimpleNamespace(id=uuid4(), kind=kind, review_status="APPROVED")


def _has_items(kinds: list[str]) -> bool:
    blocks = [_block(k) for k in kinds]
    items = {i.code: i for i in _gate(blocks, {b.id: [] for b in blocks})}
    return items["HAS_ITEMS"].ok


def test_flashcards_alone_do_not_count_as_questions() -> None:
    assert _has_items(["paragraph", "card_front", "card_back"]) is False


def test_a_worksheet_item_counts_as_a_question() -> None:
    assert _has_items(["paragraph", "worksheet_item", "option", "answer_key"]) is True
