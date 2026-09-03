"""Player model."""

from __future__ import annotations

from datetime import datetime

from app.models.base import TimestampedModel


class Player(TimestampedModel):
    """A registered Among Us player, unique per (guild, discord user)."""

    id: int | None = None
    guild_id: int
    discord_user_id: int

    among_us_name: str
    nickname: str | None = None

    faceit_player_id: str | None = None
    faceit_nickname: str | None = None

    elo: int = 1000
    peak_elo: int = 1000

    level: int = 1

    matches: int = 0
    wins: int = 0
    losses: int = 0

    win_streak: int = 0
    best_win_streak: int = 0

    total_voice_seconds: int = 0

    registered_at: datetime | None = None

    active: bool = True
    banned: bool = False
