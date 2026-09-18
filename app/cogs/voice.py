"""Voice cog — track voice channel joins/leaves."""

import discord
from discord.ext import commands

from app.repositories.player_repository import PlayerRepository
from app.services.voice_service import VoiceService
from app.supabase_client import get_client


class VoiceCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ) -> None:
        if member.bot:
            return

        guild_id = member.guild.id
        player = await PlayerRepository(get_client()).get(guild_id, member.id)
        if not player or player.id is None:
            return

        svc = VoiceService(get_client())

        if before.channel is None and after.channel is not None:
            await svc.start_session(guild_id, player.id, after.channel.id)

        elif before.channel is not None and after.channel is None:
            await svc.end_session(guild_id, player.id)

        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel != after.channel
        ):
            await svc.end_session(guild_id, player.id)
            await svc.start_session(guild_id, player.id, after.channel.id)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(VoiceCog(bot))
