"""Canonical JSON + hashes shared by services, seed and tests (D-001 #5)."""

import hashlib
import json
import unicodedata
from collections.abc import Iterable
from typing import Any


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def norm_text(text: str) -> str:
    """NFC + collapsed whitespace; Vietnamese diacritics are preserved (VAL-02)."""
    return " ".join(unicodedata.normalize("NFC", text).split())


def excerpt_hash(excerpt: str) -> str:
    return sha256_hex(norm_text(excerpt))


def content_hash(
    kind: str,
    payload: dict[str, Any],
    parent: str | None,
    transformation: str,
    no_source_reason: str | None,
) -> str:
    return sha256_hex(
        canonical_json(
            {
                "kind": kind,
                "payload": payload,
                "parent": parent,
                "transformation": transformation,
                "noSourceReason": no_source_reason,
            }
        )
    )


def source_hashes(source_revision_sha256: Iterable[str], anchor_excerpt_hashes: Iterable[str]) -> list[str]:
    """Sorted unique hashes of every VERIFIED link's source revision and anchor excerpt."""
    return sorted({*source_revision_sha256, *anchor_excerpt_hashes})
