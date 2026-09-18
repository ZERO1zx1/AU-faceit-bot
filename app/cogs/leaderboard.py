"""Leaderboard slash command."""

import discord
from discord import app_commands
from discord.ext import commands

from app.services.leaderboard_service import LeaderboardService
from app.supabase_client import get_client
from app.ui.embeds import leaderboard_embed


class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="leaderboard", description="Серверийн шилдэг 10 тоглогчийг Elo-гоор харах."
    )
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer()
        client = get_client()
        svc = LeaderboardService(client)
        players = await svc.get(interaction.guild_id, limit=10)

        embed = leaderboard_embed(players, guild_name=interaction.guild.name)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
