"""Queue entry model."""

from __future__ import annotations

from datetime import datetime

from app.models.base import SupabaseModel


class QueueEntry(SupabaseModel):
    """A player waiting in the matchmaking queue."""

    id: int | None = None
    guild_id: int
    player_id: int
    joined_at: datetime | None = None
    queue_position: int | None = None
    status: str = "WAITING"
