"""Leaderboard cog — /leaderboard."""

from discord.ext import commands

from app.db import SessionFactory
from app.services.leaderboard_service import LeaderboardService
from app.ui.embeds import leaderboard_embed


class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        async with SessionFactory() as session:
            svc = LeaderboardService(session)
            players = await svc.get(ctx.guild.id, limit=10)

        embed = leaderboard_embed(players, guild_name=ctx.guild.name)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
