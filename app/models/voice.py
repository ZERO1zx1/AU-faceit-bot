"""Voice session and voice totals models."""

from __future__ import annotations

from datetime import date, datetime

from app.models.base import SupabaseModel


class VoiceSession(SupabaseModel):
    """A single voice-channel attendance window for a player."""

    id: int | None = None
    guild_id: int
    player_id: int
    channel_id: int

    joined_at: datetime | None = None
    left_at: datetime | None = None
    duration_seconds: int | None = None


class VoiceTotal(SupabaseModel):
    """Aggregated voice time for a player bucketed by date."""

    id: int | None = None
    guild_id: int
    player_id: int
    bucket_date: date
    total_seconds: int = 0
