"""Tests for administrative player operations."""

from __future__ import annotations

from typing import Any

import discord
import pytest
from discord import app_commands
from discord.ext import commands

from app.cogs.admin import AdminCog
from app.models.player import Player
from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.services.admin_service import AdminService


async def _player(client: Any, guild_id: int = 100, user_id: int = 200) -> Player:
    await GuildRepository(client).upsert_settings(guild_id)
    return await PlayerRepository(client).create(guild_id, user_id, "AdminTarget")


async def test_adjust_elo_updates_player_and_writes_audit_log(client: Any) -> None:
    player = await _player(client)
    assert player.id is not None
    old_elo, new_elo = await AdminService(client).adjust_elo(
        100, 200, 25, actor_id=999, target_name="Target"
    )

    updated = await PlayerRepository(client).get_by_id(player.id)
    assert updated is not None
    assert (old_elo, new_elo) == (1000, 1025)
    assert updated.elo == 1025
    assert client.tables["audit_logs"][0]["action_type"] == "ELO_MANUAL"


async def test_ban_and_unban_update_player_records_and_logs(client: Any) -> None:
    player = await _player(client)
    assert player.id is not None
    service = AdminService(client)

    await service.ban_player(
        100, 200, reason="Queue abuse", actor_id=999, target_name="Target"
    )
    banned_player = await PlayerRepository(client).get_by_id(player.id)
    assert banned_player is not None
    assert banned_player.banned is True
    assert client.tables["bans"][0]["active"] is True

    await service.unban_player(100, 200, actor_id=999, target_name="Target")
    unbanned_player = await PlayerRepository(client).get_by_id(player.id)
    assert unbanned_player is not None
    assert unbanned_player.banned is False
    assert client.tables["bans"][0]["active"] is False
    assert [row["action_type"] for row in client.tables["audit_logs"]] == ["BAN", "UNBAN"]


async def test_admin_action_rejects_unregistered_player(client: Any) -> None:
    with pytest.raises(ValueError, match="Player not found"):
        await AdminService(client).adjust_elo(
            100, 404, 10, actor_id=999, target_name="Missing"
        )


async def test_admin_slash_group_registers_with_descriptions() -> None:
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    try:
        await bot.add_cog(AdminCog(bot))
        group = bot.tree.get_command("admin")
        assert group is not None
        assert group.description
        assert isinstance(group, app_commands.Group)
        assert {command.name for command in group.commands} == {"elo", "ban", "unban"}
        for command in group.commands:
            assert command.description
            assert isinstance(command, app_commands.Command)
            assert all(parameter.description for parameter in command.parameters)
    finally:
        await bot.close()
