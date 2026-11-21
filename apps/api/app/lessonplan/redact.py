# ruff: noqa: E501  (regex tables and Vietnamese cue lists read better on one line)
"""Remove people from a lesson plan before anything becomes an anchor: signature block, head-of-department, teacher names.

shortcut: heuristic (keywords + surname list, signature block only at the end of a lesson); a name written freely in the
middle of a paragraph is not found. Upgrade: a Vietnamese NER model, when a name leak is seen in practice.
"""

import re
import unicodedata

from app.lessonplan.model import Line

MASK = "[đã ẩn]"
TAIL = 14  # a signature block sits in the last lines of a lesson
SIGN_KEYS = ("to truong", "giao vien", "nguoi soan", "nguoi duyet", "duyet", "ky ten", "to chuyen mon", "ban giam hieu", "hieu truong")
SURNAMES = {"nguyen", "tran", "le", "pham", "hoang", "huynh", "phan", "vu", "vo", "dang", "bui", "do", "ho", "ngo", "duong", "ly",
            "dinh", "doan", "luong", "trinh", "truong", "mai", "ta", "ha", "cao", "lam", "kieu", "ton"}
_LABEL = re.compile(
    r"((?:giáo viên(?: bộ môn)?|gv|người soạn|họ và tên|họ tên|tổ trưởng(?: chuyên môn)?|duyệt)\s*[:：]\s*)"
    r"([A-ZÀ-Ỵ][^\W\d_]+(?:\s+[A-ZÀ-Ỵ][^\W\d_]+){1,3})", re.IGNORECASE)
_WORD = re.compile(r"^[A-ZÀ-Ỵ][^\W\d_]*$")


def fold(t: str) -> str:
    s = unicodedata.normalize("NFD", t.lower().replace("đ", "d"))
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _is_name(text: str) -> bool:
    words = text.strip().rstrip(".").split()
    return 2 <= len(words) <= 5 and all(_WORD.match(w) for w in words) and fold(words[0]) in SURNAMES


def _is_signature_key(text: str) -> bool:
    f = fold(text)
    return len(f.split()) <= 7 and any(f.startswith(k) or f"({k}" in f for k in SIGN_KEYS) and ":" not in text


def redact(lines: list[Line]) -> tuple[list[Line], int]:
    """(lines without signature blocks and with labelled names masked, number of removed or masked pieces)."""
    out: list[Line] = []
    count = 0
    tail_from = max(0, len(lines) - TAIL)
    sign_at: int | None = None
    for i in range(tail_from, len(lines)):
        if sign_at is None and _is_signature_key(lines[i].text):
            sign_at = i
    for i, ln in enumerate(lines):
        in_sign = sign_at is not None and i >= sign_at
        if in_sign and ((len(ln.text.split()) <= 7 and not ln.text.rstrip().endswith((".", ":"))) or _is_name(ln.text)):
            count += 1
            continue
        if i < 6 or i >= tail_from:  # head and tail of a lesson: a lone name is the teacher's
            if _is_name(ln.text):
                count += 1
                continue
        text, n = _LABEL.subn(lambda m: m.group(1) + MASK, ln.text)
        if n:
            count += n
            ln = Line(text, ln.page, ln.x0, ln.top, ln.bottom, ln.boxed, ln.table, ln.header, ln.wrap_ok, ln.opts)
        out.append(ln)
    return out, count
