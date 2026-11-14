"""Audit trail. Never put content (source/block text, passwords, identifiers) in `meta`."""

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models as m


def audit(
    db: AsyncSession, actor_id: UUID | None, action: str, resource_type: str, resource_id: UUID | None = None
) -> None:
    db.add(m.AuditLog(actor_id=actor_id, action=action, resource_type=resource_type, resource_id=resource_id))
