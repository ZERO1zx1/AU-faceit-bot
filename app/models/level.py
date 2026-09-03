"""Level role model for FACEIT-style level boundaries."""

from __future__ import annotations

from app.models.base import SupabaseModel


class LevelRole(SupabaseModel):
    """Maps a level (1-10) to an optional Elo bound and Discord role."""

    id: int | None = None
    guild_id: int
    level: int
    min_elo: int | None = None
    max_elo: int | None = None
    role_id: int | None = None
