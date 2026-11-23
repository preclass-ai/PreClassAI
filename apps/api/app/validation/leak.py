"""VAL-10: does anything a student sees BEFORE answering an item reveal that item's answer? (every subject)

Pure functions, shared by the validation runner (live blocks) and `scripts/ops/check_seed_leak.py` (published snapshots).
Heuristics, on purpose conservative about what is a BLOCKER:
- NUMBER (BLOCKER): a numeric item's answer value appears in any other visible text.
- OPTION_WITH_CUE (BLOCKER): a visible sentence names the correct option and ranks it ("... lớn nhất", "đứng đầu").
- SINGLED_OUT (BLOCKER): the only option named by the visible data facts is the correct one.
- CUE_TOKEN (WARNING): a ranking sentence uses a word that only the correct option has ("vùng núi" vs "Trung du và miền núi").
- NARROWS (WARNING): a paragraph/instruction/other question names some but not all options, including the correct one.
shortcut: wording tricks the heuristics do not model (paraphrase, synonyms) pass; the teacher review is the last line.
"""

import re
import unicodedata
from decimal import Decimal, InvalidOperation
from typing import Any

from app.sources.numbers import parse_numbers

CUE_PHRASES = ("dung dau", "hang dau", "so mot", "vuot troi")
TOL = Decimal("0.05")
BLOCKER_KINDS = {"NUMBER", "OPTION_WITH_CUE", "SINGLED_OUT"}


def norm(s: str) -> str:
    """Lower case, no diacritics, words only (same as `app.habit.rules.norm`; copied to keep this module import-light)."""
    d = unicodedata.normalize("NFD", s.lower().replace("đ", "d"))
    d = "".join(c for c in d if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", d)).strip()


def visible_text(kind: str, p: dict[str, Any]) -> str:
    """The text a student reads for a block (a data fact is read as "label value unit period region")."""
    if kind == "data_fact":
        v = p.get("value")
        return " ".join(str(x) for x in (p.get("label"), str(v).replace(".", ",") if v is not None else "", p.get("unit"),
                                         p.get("period"), p.get("region")) if x)
    if kind == "review_card":  # study card shown before the quiz: title, points, example and its own self-check
        chk: dict[str, Any] = p["check"] if isinstance(p.get("check"), dict) else {}
        parts = (p.get("title"), *p.get("points", []), p.get("example"), chk.get("statement"), chk.get("explanation"))
        return " ".join(str(x) for x in parts if x)
    return str(p.get("stem") or p.get("text") or "")


def _has_cue(nsent: str) -> bool:
    padded = f" {nsent} "
    return " nhat " in padded or any(f" {p} " in padded for p in CUE_PHRASES)


def _words(text: str) -> set[str]:
    """Lower-case words WITH diacritics (bảng ≠ bằng): used where a stripped match would be a false positive."""
    return {w for w in re.findall(r"\w+", text.lower()) if len(w) >= 3}


def _sentences(text: str) -> list[str]:
    return [s for s in re.split(r"[.!?;\n]+", text) if s.strip()]


def item_answer_leaks(item_type: str, options: list[tuple[str, str]], key: dict[str, Any],
                      visible: list[tuple[str, str, str]]) -> list[dict[str, str]]:
    """`visible`: (block id, kind, text) of everything shown before this item is answered, except this item itself.
    kind: heading | paragraph | instruction | data_fact | card_front | stem (another question's stem)."""
    out: list[dict[str, str]] = []
    if item_type == "NUMERIC" and key.get("value") is not None:
        try:
            want = Decimal(str(key["value"]))
        except InvalidOperation:
            want = None
        for bid, kind, text in visible:
            if want is not None and any(abs(n - want) <= TOL for n in parse_numbers(text)):
                out.append({"kind": "NUMBER", "block": bid, "in": kind})
        return out
    correct = key.get("correct")
    texts = {lab: norm(t) for lab, t in options}
    if item_type != "MCQ" or correct not in texts or not texts[correct]:
        return out
    own = {lab: _words(t) for lab, t in options}
    distinct = own[correct].difference(*(w for lab, w in own.items() if lab != correct))
    facts_named: set[str] = set()
    for bid, kind, text in visible:
        ntext = f" {norm(text)} "
        named = {lab for lab, t in texts.items() if t and f" {t} " in ntext}
        if kind == "data_fact":
            facts_named |= named
        for sent in _sentences(text):
            ns = norm(sent)
            if not _has_cue(ns):
                continue
            if correct in {lab for lab, t in texts.items() if t and f" {t} " in f" {ns} "}:
                out.append({"kind": "OPTION_WITH_CUE", "block": bid, "in": kind})
            elif distinct & _words(sent):
                out.append({"kind": "CUE_TOKEN", "block": bid, "in": kind})
        if kind in ("paragraph", "instruction", "heading", "stem") and correct in named and len(named) < len(texts):
            out.append({"kind": "NARROWS", "block": bid, "in": kind})
    if facts_named == {correct}:
        out.append({"kind": "SINGLED_OUT", "block": "data_fact", "in": "data_fact"})
    return out


def severity(findings: list[dict[str, str]]) -> str:
    return "BLOCKER" if any(f["kind"] in BLOCKER_KINDS for f in findings) else "WARNING"
