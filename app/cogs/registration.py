"""Registration cog — /unregister with confirmation."""

import discord
from discord import app_commands
from discord.ext import commands

from app.services.registration_service import RegistrationService
from app.supabase_client import get_client
from app.ui.views import UnregisterConfirmView


class RegistrationCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(
        name="unregister", description="AU FACEIT бүртгэлээ устгах хүсэлт гаргах."
    )
    @app_commands.guild_only()
    async def unregister(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        client = get_client()
        svc = RegistrationService(client)
        player = await svc.get(guild.id, interaction.user.id)
        if not player:
            await interaction.followup.send("Та бүртгэлгүй байна.", ephemeral=True)
            return

        embed = discord.Embed(
            title="⚠️ Unregister",
            description="Та AU FACEIT бүртгэлээ устгахдаа итгэлтэй байна уу?\n\n"
            "**Note:** Active queue/match-д байвал unregister хийхгүй.",
            color=discord.Color.orange(),
        )
        view = UnregisterConfirmView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RegistrationCog(bot))
