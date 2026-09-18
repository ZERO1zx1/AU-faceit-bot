"""Described ``/admin`` slash-command group."""

import contextlib

import discord
from discord import app_commands
from discord.ext import commands

from app.cogs.faceit_level import FaceitLevelCog
from app.services.admin_service import AdminService
from app.supabase_client import get_client


def admin_embed(title: str, description: str, *, success: bool = True) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green() if success else discord.Color.red(),
    )


class AdminCog(commands.Cog):
    admin = app_commands.Group(
        name="admin",
        description="AU FACEIT тоглогч болон серверийн admin үйлдлүүд.",
        guild_only=True,
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @admin.command(name="elo", description="Тоглогчийн Elo оноог гараар нэмэх эсвэл хасах.")
    @app_commands.describe(
        member="Elo-г өөрчлөх бүртгэлтэй тоглогч.",
        amount="Нэмэх эерэг эсвэл хасах сөрөг Elo хэмжээ.",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def elo_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        amount: app_commands.Range[int, -1000, 1000],
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        service = AdminService(get_client(), self.bot)
        try:
            old_elo, new_elo = await service.adjust_elo(
                guild.id,
                member.id,
                amount,
                actor_id=interaction.user.id,
                target_name=member.display_name,
            )
        except ValueError as exc:
            await interaction.followup.send(
                embed=admin_embed("❌ Elo өөрчилж чадсангүй", str(exc), success=False),
                ephemeral=True,
            )
            return
        faceit = self.bot.get_cog("FaceitLevelCog")
        if isinstance(faceit, FaceitLevelCog):
            with contextlib.suppress(Exception):
                await faceit.sync_member_level(member)
        await interaction.followup.send(
            embed=admin_embed(
                "✅ Elo шинэчлэгдлээ",
                f"{member.mention}\n**{old_elo} → {new_elo}** ({amount:+d})",
            ),
            ephemeral=True,
        )

    @admin.command(name="ban", description="Тоглогчийг AU FACEIT системээс хориглох.")
    @app_commands.describe(
        member="Хориглох бүртгэлтэй тоглогч.",
        reason="Хориг тавьж буй шалтгаан.",
    )
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def ban_slash(
        self,
        interaction: discord.Interaction,
        member: discord.Member,
        reason: str = "No reason",
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        service = AdminService(get_client(), self.bot)
        try:
            await service.ban_player(
                guild.id,
                member.id,
                reason=reason,
                actor_id=interaction.user.id,
                target_name=member.display_name,
            )
        except ValueError as exc:
            await interaction.followup.send(
                embed=admin_embed("❌ Ban хийж чадсангүй", str(exc), success=False),
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            embed=admin_embed("🔨 Тоглогч хориглогдлоо", f"{member.mention}\n**Reason:** {reason}"),
            ephemeral=True,
        )

    @admin.command(name="unban", description="Тоглогчийн AU FACEIT хоригийг цуцлах.")
    @app_commands.describe(member="Хоригийг цуцлах бүртгэлтэй тоглогч.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def unban_slash(self, interaction: discord.Interaction, member: discord.Member) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        service = AdminService(get_client(), self.bot)
        try:
            await service.unban_player(
                guild.id,
                member.id,
                actor_id=interaction.user.id,
                target_name=member.display_name,
            )
        except ValueError as exc:
            await interaction.followup.send(
                embed=admin_embed("❌ Unban хийж чадсангүй", str(exc), success=False),
                ephemeral=True,
            )
            return
        await interaction.followup.send(
            embed=admin_embed("✅ Тоглогчийн хориг цуцлагдлаа", member.mention),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(AdminCog(bot))
