"""Tests for administrative player operations."""

import discord
import pytest
from discord.ext import commands

from app.cogs.admin import AdminCog
from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.services.admin_service import AdminService


async def _player(client, guild_id: int = 100, user_id: int = 200):
    await GuildRepository(client).upsert_settings(guild_id)
    return await PlayerRepository(client).create(guild_id, user_id, "AdminTarget")


async def test_adjust_elo_updates_player_and_writes_audit_log(client):
    player = await _player(client)
    old_elo, new_elo = await AdminService(client).adjust_elo(
        100, 200, 25, actor_id=999, target_name="Target"
    )

    updated = await PlayerRepository(client).get_by_id(player.id)
    assert (old_elo, new_elo) == (1000, 1025)
    assert updated.elo == 1025
    assert client.tables["audit_logs"][0]["action_type"] == "ELO_MANUAL"


async def test_ban_and_unban_update_player_records_and_logs(client):
    player = await _player(client)
    service = AdminService(client)

    await service.ban_player(
        100, 200, reason="Queue abuse", actor_id=999, target_name="Target"
    )
    assert (await PlayerRepository(client).get_by_id(player.id)).banned is True
    assert client.tables["bans"][0]["active"] is True

    await service.unban_player(100, 200, actor_id=999, target_name="Target")
    assert (await PlayerRepository(client).get_by_id(player.id)).banned is False
    assert client.tables["bans"][0]["active"] is False
    assert [row["action_type"] for row in client.tables["audit_logs"]] == ["BAN", "UNBAN"]


async def test_admin_action_rejects_unregistered_player(client):
    with pytest.raises(ValueError, match="Player not found"):
        await AdminService(client).adjust_elo(
            100, 404, 10, actor_id=999, target_name="Missing"
        )


async def test_admin_slash_group_registers_with_descriptions():
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    try:
        await bot.add_cog(AdminCog(bot))
        group = bot.tree.get_command("admin")
        assert group is not None
        assert group.description
        assert {command.name for command in group.commands} == {"elo", "ban", "unban"}
        for command in group.commands:
            assert command.description
            assert all(parameter.description for parameter in command.parameters)
    finally:
        await bot.close()
