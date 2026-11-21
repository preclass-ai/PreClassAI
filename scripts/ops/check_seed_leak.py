"""Seed audit: can a student read an answer from what the seed lessons show BEFORE answering? (VAL-10 on the six seed lessons)

Run (no database):  cd apps/api && PYTHONPATH=. uv run python ../../scripts/ops/check_seed_leak.py
Checks every question of every seed lesson against everything shown before answering (headings, paragraphs, instructions,
data facts, the other questions' stems) with the same rules as VAL-10 (`app/validation/leak.py`), and that the right
answer is not always in the same position. Exit code 1 on any finding.
"""

import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api"))

from app.validation.leak import item_answer_leaks, visible_text  # noqa: E402
from tests.habit_support import snapshots  # noqa: E402

SHOWN = ("heading", "paragraph", "instruction", "data_fact", "card_front")


def audit() -> tuple[list[str], Counter[str], int]:
    bad: list[str] = []
    labels: Counter[str] = Counter()
    n_items = 0
    for snap, spec in snapshots():
        blocks = snap["blocks"]
        items = [b for b in blocks if b["kind"] == "worksheet_item"]
        for it in items:
            n_items += 1
            kids = [b for b in blocks if b["parentId"] == it["id"]]
            key = next((k["payload"] for k in kids if k["kind"] == "answer_key"), {})
            opts = sorted((k["payload"]["label"], k["payload"]["text"]) for k in kids if k["kind"] == "option")
            visible = [(b["id"], b["kind"], visible_text(b["kind"], b["payload"])) for b in blocks if b["kind"] in SHOWN]
            visible += [(o["id"], "stem", o["payload"]["stem"]) for o in items if o["id"] != it["id"]]
            for f in item_answer_leaks(it["payload"]["itemType"], opts, key, visible):
                bad.append(f"{spec['key']}: {it['payload']['stem'][:48]!r}: {f['kind']} in {f['in']}")
            if it["payload"]["itemType"] == "MCQ":
                labels[key.get("correct", "?")] += 1
    return bad, labels, n_items


def main() -> int:
    bad, labels, n_items = audit()
    print(f"questions checked: {n_items} (6 seed lessons); correct option position: {dict(sorted(labels.items()))}")
    if len(labels) < 3:
        bad.append(f"the right answer is in too few positions: {dict(labels)}")
    print(f"violations: {len(bad)}")
    for b in bad:
        print("  ", b)
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
