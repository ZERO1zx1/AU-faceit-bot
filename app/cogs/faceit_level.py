"""Faceit Level cog — level role syncing."""

import discord
from discord.ext import commands

from app.models.player import Player
from app.services.level_service import LevelService
from app.services.log_service import LogService
from app.services.player_service import PlayerService
from app.supabase_client import get_client


class FaceitLevelCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def sync_member_level(self, member: discord.Member) -> None:
        """Recompute a member's level from their live Elo and sync the role."""
        client = get_client()
        player = await PlayerService(client).get(member.guild.id, member.id)
        if not player or not player.id:
            return
        changed = await LevelService(client).refresh_player_level(
            member.guild.id, player.id, member
        )
        if changed:
            await LogService(client, self.bot).log(
                member.guild.id,
                "LEVEL_CHANGE",
                actor_id=member.id,
                target_entity=f"Level {changed[0]} → {changed[1]}",
                details={"player_id": player.id},
            )

    async def sync_level(self, member: discord.Member, player: Player) -> None:
        """Sync level role after elo change (legacy signature)."""
        if not player.id:
            return
        changed = await LevelService(get_client()).refresh_player_level(
            member.guild.id, player.id, member
        )
        if changed:
            log_svc = LogService(get_client(), self.bot)
            await log_svc.log(
                member.guild.id,
                "LEVEL_CHANGE",
                actor_id=member.id,
                target_entity=f"Level {changed[0]} → {changed[1]}",
                details={"player_id": player.id},
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(FaceitLevelCog(bot))
