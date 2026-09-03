"""Ban model."""

from __future__ import annotations

from datetime import datetime

from app.models.base import SupabaseModel


class Ban(SupabaseModel):
    """A player ban record."""

    id: int | None = None
    guild_id: int
    player_id: int
    reason: str | None = None
    banned_by: int | None = None
    active: bool = True
    banned_at: datetime | None = None
    unbanned_at: datetime | None = None
