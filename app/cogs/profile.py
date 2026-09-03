"""Profile cog — /profile, /matches."""

import discord
from discord.ext import commands
from sqlalchemy import select

from app.db import SessionFactory
from app.models.player import Player
from app.repositories.elo_repository import EloRepository
from app.services.leaderboard_service import LeaderboardService
from app.services.player_service import PlayerService
from app.ui.embeds import profile_embed


class ProfileCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profile")
    async def profile(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        async with SessionFactory() as session:
            svc = PlayerService(session)
            player = await svc.get(ctx.guild.id, member.id)
            if not player:
                return await ctx.send("Бүртгүүлээгүй байна.")
            lb_svc = LeaderboardService(session)
            lb = await lb_svc.get(ctx.guild.id, limit=100)
            rank = next(
                (i + 1 for i, p in enumerate(lb) if p.discord_user_id == member.id), None
            )

        embed = profile_embed(member, player)
        if rank:
            embed.set_footer(text=f"Rank #{rank}")
        await ctx.send(embed=embed)

    @commands.command(name="matches")
    async def matches(self, ctx: commands.Context, member: discord.Member = None):
        member = member or ctx.author
        async with SessionFactory() as session:
            elo_repo = EloRepository(session)
            res = await session.execute(
                select(Player).where(
                    Player.guild_id == ctx.guild.id,
                    Player.discord_user_id == member.id,
                )
            )
            player = res.scalar_one_or_none()
            if not player:
                return await ctx.send("Бүртгүүлээгүй байна.")
            history = await elo_repo.get_history(player.id, limit=20)

        if not history:
            return await ctx.send("Match түүх байхгүй байна.")

        lines = []
        for tx in history:
            sign = "+" if tx.change > 0 else ""
            lines.append(
                f"**{tx.reason or 'Elo change'}** — {tx.old_elo} → "
                f"{tx.new_elo} ({sign}{tx.change})"
            )
        embed = discord.Embed(
            title=f"━━━ {member.display_name} — Match History ━━━",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(ProfileCog(bot))
