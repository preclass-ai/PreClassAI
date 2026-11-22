"""Error text the API shows to people: "em" for students, "thầy cô" for teachers, never "Bạn"; no long dash."""

import re
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
MESSAGE = re.compile(r"ApiError\([^\n]*?\"([^\"\n]+)\"\s*[,)]")  # the last string literal of an ApiError(...) call is its text


def test_api_error_messages_do_not_say_ban_or_use_long_dashes() -> None:
    bad = []
    for f in APP.rglob("*.py"):
        for n, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            for text in MESSAGE.findall(line):
                if re.search(r"\b[Bb]ạn\b", text) or "—" in text:
                    bad.append(f"{f.relative_to(APP)}:{n}")
    assert bad == []
