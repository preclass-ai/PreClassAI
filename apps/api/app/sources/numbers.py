"""Single Vietnamese number parser for anchors and payloads (D-001 #3).

Vietnamese: '.' groups thousands, ',' is the decimal mark. A lone "1.234" is ambiguous, so both
readings (1234 and 1.234) are returned and either may match a payload number.
"""

import re
from decimal import Decimal

_NUM = re.compile(r"(?<![\w.,])\d[\d.,]*(?![\w])")
_GROUPED = re.compile(r"^\d{1,3}(\.\d{3})+$")


def _read(token: str) -> list[Decimal]:
    token = token.rstrip(".,")
    if "," in token:
        whole, _, frac = token.rpartition(",")
        whole = whole.replace(".", "")
        if not whole.isdigit() or not frac.isdigit():
            return []
        return [Decimal(f"{whole}.{frac}")]
    if "." not in token:
        return [Decimal(token)]
    if _GROUPED.match(token):
        grouped = Decimal(token.replace(".", ""))
        if token.count(".") == 1:  # "1.234": thousands or decimal
            return [grouped, Decimal(token)]
        return [grouped]
    whole, _, frac = token.rpartition(".")
    return [Decimal(token)] if whole.replace(".", "").isdigit() and frac.isdigit() else []


def parse_numbers(text: str) -> list[Decimal]:
    """All candidate numbers in `text`, in order, ambiguous tokens yielding two candidates."""
    out: list[Decimal] = []
    for m in _NUM.finditer(text):
        out.extend(_read(m.group()))
    return out
