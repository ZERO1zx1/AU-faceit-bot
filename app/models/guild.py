"""Guild and GuildSettings models."""

from __future__ import annotations

from app.models.base import TimestampedModel


class Guild(TimestampedModel):
    """A Discord guild (server) that has enabled the bot."""

    id: int
    enabled: bool = True


class GuildSettings(TimestampedModel):
    """Per-guild matchmaking configuration and channel bindings."""

    guild_id: int

    admin_role_id: int | None = None
    moderator_role_id: int | None = None
    registered_role_id: int | None = None

    register_channel_id: int | None = None
    register_message_id: int | None = None

    queue_channel_id: int | None = None
    queue_message_id: int | None = None

    leaderboard_channel_id: int | None = None
    leaderboard_message_id: int | None = None

    match_category_id: int | None = None

    log_channel_id: int | None = None

    default_elo: int = 1000
    win_elo: int = 8
    loss_elo: int = -6

    queue_size: int = 15
    nickname_format: str | None = None
