"""Leaderboard cog — /leaderboard."""

from discord.ext import commands

from app.services.leaderboard_service import LeaderboardService
from app.supabase_client import get_client
from app.ui.embeds import leaderboard_embed


class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx: commands.Context):
        client = get_client()
        svc = LeaderboardService(client)
        players = await svc.get(ctx.guild.id, limit=10)

        embed = leaderboard_embed(players, guild_name=ctx.guild.name)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
