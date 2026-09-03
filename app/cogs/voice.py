"""Voice cog — track voice channel joins/leaves."""

import discord
from discord.ext import commands

from app.db import SessionFactory
from app.services.voice_service import VoiceService


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

        if before.channel is None and after.channel is not None:
            async with SessionFactory() as session:
                svc = VoiceService(session)
                await svc.start_session(member.guild.id, member.id, after.channel.id)
                await session.commit()

        elif before.channel is not None and after.channel is None:
            async with SessionFactory() as session:
                svc = VoiceService(session)
                await svc.end_session(member.guild.id, member.id)
                await session.commit()

        elif (
            before.channel is not None
            and after.channel is not None
            and before.channel != after.channel
        ):
            async with SessionFactory() as session:
                svc = VoiceService(session)
                await svc.end_session(member.guild.id, member.id)
                await svc.start_session(member.guild.id, member.id, after.channel.id)
                await session.commit()


async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
