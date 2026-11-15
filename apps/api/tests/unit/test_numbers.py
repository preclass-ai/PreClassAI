from decimal import Decimal as D

import pytest

from app.sources.numbers import parse_numbers


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("1.234,5", [D("1234.5")]),
        ("12,5", [D("12.5")]),
        ("2020", [D("2020")]),
        ("1.234", [D("1234"), D("1.234")]),  # ambiguous: both readings
        ("12.345.678", [D("12345678")]),
        ("Dân số 98,5 triệu người năm 2021.", [D("98.5"), D("2021")]),
        ("a1.5b", []),
    ],
)
def test_parse_numbers(text: str, expected: list[D]) -> None:
    assert parse_numbers(text) == expected


def test_text_table_becomes_cell_anchors() -> None:
    from app.sources.parse import parse_text
    a = parse_text("Bảng\n\nGhi chú.\n\n| Vùng | Dân số |\n|---|---|\n| A | 23,2 |\n| B | 5,9 |")
    cells = [x for x in a if x.kind == "TABLE_CELL"]
    assert [x.kind for x in a[:2]] == ["HEADING", "PARAGRAPH"] and len(cells) == 6
    assert cells[3].locator == {"table": 0, "row": 1, "col": 1} and cells[3].numbers == [D("23.2")]
    assert [x.kind for x in parse_text("a\n\nb | c")] == ["HEADING", "PARAGRAPH"]  # one line is not a table
