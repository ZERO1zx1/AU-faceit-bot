"""Small offline Discord interaction doubles for end-to-end component tests."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock


def interaction(
    *,
    guild_id: int = 100,
    user_id: int = 200,
    bot: Any | None = None,
) -> SimpleNamespace:
    """Build the subset of ``discord.Interaction`` used by this project."""
    response = SimpleNamespace(
        send_message=AsyncMock(),
        defer=AsyncMock(),
        edit_message=AsyncMock(),
        send_modal=AsyncMock(),
        is_done=lambda: False,
    )
    followup = SimpleNamespace(send=AsyncMock())
    guild = SimpleNamespace(
        id=guild_id,
        get_channel=lambda _channel_id: None,
        get_role=lambda _role_id: None,
        get_member=lambda _user_id: None,
        fetch_channel=AsyncMock(return_value=None),
    )
    user = SimpleNamespace(id=user_id)
    client = bot or SimpleNamespace(get_cog=lambda _name: None)
    return SimpleNamespace(
        guild_id=guild_id,
        channel_id=300,
        guild=guild,
        user=user,
        client=client,
        response=response,
        followup=followup,
        message=None,
    )


def set_text_input(modal: Any, field: str, value: str) -> None:
    """Set a Discord ``TextInput`` value without a live Discord payload."""
    getattr(modal, field)._value = value
