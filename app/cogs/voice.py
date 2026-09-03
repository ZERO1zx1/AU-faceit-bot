"""Voice cog — track voice channel joins/leaves."""

import discord
from discord.ext import commands

from app.services.voice_service import VoiceService
from app.supabase_client import get_client


class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(
        self,
        member: discord.Member,
        before: discord.VoiceState,
        after: discord.VoiceState,
    ):
        if member.bot:
            return

        svc = VoiceService(get_client())

        if before.channel is None and after.channel is not None:
            await svc.start_session(member.guild.id, member.id, after.channel.id)

        elif before.channel is not None and after.channel is None:
            await svc.end_session(member.guild.id, member.id)

        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel != after.channel
        ):
            await svc.end_session(member.guild.id, member.id)
            await svc.start_session(member.guild.id, member.id, after.channel.id)


async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
