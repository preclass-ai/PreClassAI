"""Write apps/api/openapi/openapi.json from the FastAPI app (CI fails when the committed file drifts)."""

import json
from pathlib import Path

from app.main import app

OUT = Path(__file__).resolve().parents[1] / "openapi" / "openapi.json"


def render() -> str:
    return json.dumps(app.openapi(), ensure_ascii=False, indent=2, sort_keys=True) + "\n"


if __name__ == "__main__":
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(render(), encoding="utf-8", newline="\n")
    print(f"wrote {OUT}")
