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
