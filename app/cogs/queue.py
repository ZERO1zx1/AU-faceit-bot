"""Queue status slash command."""

import discord
from discord import app_commands
from discord.ext import commands

from app.services.queue_service import QueueService
from app.services.setup_service import SetupService
from app.supabase_client import get_client
from app.ui.embeds import queue_embed


class QueueCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="queue-status", description="Одоогийн queue-ийн хүн болон дундаж Elo-г харах."
    )
    @app_commands.guild_only()
    async def queue_status(self, interaction: discord.Interaction):
        await interaction.response.defer()
        client = get_client()
        settings = await SetupService(client).get_settings(interaction.guild_id)
        queue_size = settings.queue_size if settings else 15
        svc = QueueService(client, queue_size=queue_size)
        count, avg_elo = await svc.get_status(interaction.guild_id)
        embed = queue_embed(count=count, max_size=queue_size, avg_elo=avg_elo)
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(QueueCog(bot))
