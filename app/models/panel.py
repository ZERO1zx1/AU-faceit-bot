"""Panel model for persistent custom panels."""

from __future__ import annotations

from app.models.base import SupabaseModel


class Panel(SupabaseModel):
    """A persistent custom embed panel configured by a server admin."""

    id: int | None = None
    guild_id: int
    type: str

    channel_id: int | None = None
    message_id: int | None = None

    title: str | None = None
    description: str | None = None
    color: int | None = None

    thumbnail_url: str | None = None
    image_url: str | None = None
    footer: str | None = None

    configuration_json: str | None = None
