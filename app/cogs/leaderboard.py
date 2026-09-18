"""Leaderboard slash command."""

import discord
from discord import app_commands
from discord.ext import commands

from app.services.leaderboard_service import LeaderboardService
from app.supabase_client import get_client
from app.ui.embeds import leaderboard_embed


class LeaderboardCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="leaderboard", description="Серверийн шилдэг 10 тоглогчийг Elo-гоор харах."
    )
    @app_commands.guild_only()
    async def leaderboard(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        guild = interaction.guild
        if guild is None:
            return
        client = get_client()
        svc = LeaderboardService(client)
        players = await svc.get(guild.id, limit=10)

        embed = leaderboard_embed(players, guild_name=guild.name)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(LeaderboardCog(bot))
