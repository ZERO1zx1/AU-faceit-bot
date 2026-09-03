"""Faceit Level cog — level role syncing."""

import discord
from discord.ext import commands

from app.services.level_service import LevelService
from app.services.log_service import LogService
from app.supabase_client import get_client


class FaceitLevelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def sync_level(self, member: discord.Member, player):
        """Sync level role after elo change."""
        client = get_client()
        svc = LevelService(client)
        old_level = player.level
        new_level = await svc.update_player_level(player)
        if old_level != new_level:
            await svc.sync_role(member, old_level, new_level)
            log_svc = LogService(client)
            await log_svc.log(
                member.guild.id, "LEVEL_CHANGE",
                actor_id=member.id,
                target_entity=f"Level {old_level} → {new_level}",
            )


async def setup(bot):
    await bot.add_cog(FaceitLevelCog(bot))
