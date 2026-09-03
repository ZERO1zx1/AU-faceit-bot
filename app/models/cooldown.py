"""Cooldown model for rate limiting sensitive actions."""

from __future__ import annotations

from datetime import datetime

from app.models.base import SupabaseModel


class Cooldown(SupabaseModel):
    """A per-(guild, user, action) cooldown window."""

    id: int | None = None
    guild_id: int
    user_id: int
    action: str
    expires_at: datetime
