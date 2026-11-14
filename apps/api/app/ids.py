"""Deterministic ids: the seed and the OpenAPI examples share them, so examples match real seed rows."""

import uuid

NS = uuid.UUID("6f1c0d6e-2b7a-4f57-9a55-5a1d0c0de001")


def uid(name: str) -> uuid.UUID:
    return uuid.uuid5(NS, name)
