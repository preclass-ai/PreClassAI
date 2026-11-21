"""Humanized copy: no long dashes in the reply templates students read (UI strings are checked in apps/web/tests/copy.test.ts)."""

import io
import tokenize
from pathlib import Path

HABIT = Path(__file__).resolve().parents[2] / "app" / "habit"


def test_no_em_dash_or_spaced_en_dash_in_habit_strings() -> None:
    bad = []
    for f in HABIT.glob("*.py"):
        for tok in tokenize.generate_tokens(io.StringIO(f.read_text(encoding="utf-8")).readline):
            if tok.type == tokenize.STRING and ("—" in tok.string or " – " in tok.string):
                bad.append(f"{f.name}:{tok.start[0]}")
    assert bad == [], bad


def test_replies_call_the_assistant_habit_ai() -> None:
    from app.habit import llm, rules

    texts = [*rules.REFUSAL.values(), llm.SYSTEM]
    assert not [t for t in texts if "Habit" in t.replace("HABIT AI", "")], texts
