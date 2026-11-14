"""Published snapshot builder (PR-05). Internal shape; students only ever get whitelist DTOs."""

from typing import Any

from app.hashing import canonical_json, sha256_hex


def build_snapshot(title: str, grade: int, blocks: list[dict[str, Any]]) -> tuple[dict[str, Any], str]:
    """`blocks`: dicts with id, kind, parent_id, position, payload (approved, non-deleted)."""
    snap = {
        "title": title,
        "grade": grade,
        "blocks": [
            {
                "id": str(b["id"]),
                "kind": b["kind"],
                "parentId": str(b["parent_id"]) if b["parent_id"] else None,
                "position": b["position"],
                "payload": b["payload"],
            }
            for b in sorted(blocks, key=lambda b: b["position"])
        ],
    }
    return snap, sha256_hex(canonical_json(snap))
