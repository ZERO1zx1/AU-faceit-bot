"""Audit log model."""

from __future__ import annotations

from datetime import datetime

from app.models.base import SupabaseModel


class AuditLog(SupabaseModel):
    """A single audit log entry for sensitive bot actions."""

    id: int | None = None
    guild_id: int
    action_type: str
    actor_id: int | None = None
    target_entity: str | None = None
    details: str | None = None
    success: bool = True
    error_message: str | None = None
    created_at: datetime | None = None
