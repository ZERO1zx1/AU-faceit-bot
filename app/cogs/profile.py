"""Profile cog — /profile, /matches."""

import discord
from discord import app_commands
from discord.ext import commands

from app.services.leaderboard_service import LeaderboardService
from app.services.player_service import PlayerService
from app.supabase_client import get_client
from app.ui.embeds import profile_embed


class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="profile", description="Өөрийн эсвэл тоглогчийн AU FACEIT профайлыг харах."
    )
    @app_commands.describe(member="Профайлыг нь харах тоглогч; хоосон бол өөрийн профайл.")
    @app_commands.guild_only()
    async def profile(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await interaction.response.defer()
        member = member or interaction.user
        client = get_client()
        svc = PlayerService(client)
        player = await svc.get(interaction.guild_id, member.id)
        if not player:
            await interaction.followup.send("Бүртгүүлээгүй байна.", ephemeral=True)
            return
        lb_svc = LeaderboardService(client)
        lb = await lb_svc.get(interaction.guild_id, limit=100)
        rank = next((i + 1 for i, p in enumerate(lb) if p.discord_user_id == member.id), None)

        embed = profile_embed(member, player)
        if rank:
            embed.set_footer(text=f"Rank #{rank}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="matches", description="Тоглогчийн сүүлийн Elo өөрчлөлтийн түүхийг харах."
    )
    @app_commands.describe(member="Түүхийг нь харах тоглогч; хоосон бол өөрийн түүх.")
    @app_commands.guild_only()
    async def matches(self, interaction: discord.Interaction, member: discord.Member | None = None):
        await interaction.response.defer()
        member = member or interaction.user
        client = get_client()
        svc = PlayerService(client)
        player = await svc.get(interaction.guild_id, member.id)
        if not player:
            await interaction.followup.send("Бүртгүүлээгүй байна.", ephemeral=True)
            return

        history = await svc.get_history(player.id, limit=20)
        if not history:
            await interaction.followup.send("Match түүх байхгүй байна.", ephemeral=True)
            return

        lines = []
        for tx in history:
            sign = "+" if tx.change > 0 else ""
            lines.append(
                f"**{tx.reason or 'Elo change'}** — {tx.old_elo} → {tx.new_elo} ({sign}{tx.change})"
            )
        embed = discord.Embed(
            title=f"━━━ {member.display_name} — Match History ━━━",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await interaction.followup.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
