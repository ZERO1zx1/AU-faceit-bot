"""Elo transaction model for audit-safe Elo history."""

from __future__ import annotations

from app.models.base import TimestampedModel


class EloTransaction(TimestampedModel):
    """A single Elo change applied to a player."""

    id: int | None = None
    guild_id: int
    player_id: int
    match_id: int | None = None

    old_elo: int
    change: int
    new_elo: int

    reason: str | None = None
    transaction_type: str = "MATCH"

    created_by: int | None = None
