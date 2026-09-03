"""Admin cog — /player elo, /player ban, /player unban, /match cancel."""

import discord
from discord.ext import commands
from sqlalchemy import select

from app.db import SessionFactory
from app.models.ban import Ban
from app.repositories.player_repository import PlayerRepository
from app.services.log_service import LogService


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="elo")
    @commands.has_permissions(manage_guild=True)
    async def elo(self, ctx: commands.Context, member: discord.Member, amount: int):
        async with SessionFactory() as session:
            repo = PlayerRepository(session)
            player = await repo.get(ctx.guild.id, member.id)
            if not player:
                return await ctx.send("Player not found.")
            old_elo = player.elo
            player.elo += amount
            player.peak_elo = max(player.peak_elo, player.elo)
            log_svc = LogService(session)
            await log_svc.log(
                ctx.guild.id, "ELO_MANUAL",
                actor_id=ctx.author.id,
                target_entity=member.display_name,
                details={"old": old_elo, "new": player.elo, "delta": amount},
            )
            await session.commit()
        await ctx.send(f"✅ {member.mention} Elo: {old_elo} → {player.elo}")

    @commands.command(name="ban")
    @commands.has_permissions(manage_guild=True)
    async def ban(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"
    ):
        async with SessionFactory() as session:
            repo = PlayerRepository(session)
            player = await repo.get(ctx.guild.id, member.id)
            if not player:
                return await ctx.send("Player not found.")
            player.banned = True
            ban = Ban(
                guild_id=ctx.guild.id, player_id=player.id,
                reason=reason, banned_by=ctx.author.id,
            )
            session.add(ban)
            log_svc = LogService(session)
            await log_svc.log(
                ctx.guild.id, "BAN", actor_id=ctx.author.id,
                target_entity=member.display_name, details={"reason": reason},
            )
            await session.commit()
        await ctx.send(f"🔨 {member.mention} banned: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(manage_guild=True)
    async def unban(self, ctx: commands.Context, member: discord.Member):
        async with SessionFactory() as session:
            repo = PlayerRepository(session)
            player = await repo.get(ctx.guild.id, member.id)
            if not player:
                return await ctx.send("Player not found.")
            player.banned = False
            res = await session.execute(
                select(Ban).where(Ban.player_id == player.id, Ban.active).limit(1)
            )
            ban = res.scalar_one_or_none()
            if ban:
                ban.active = False
            await session.commit()
        await ctx.send(f"✅ {member.mention} unbanned")


async def setup(bot):
    await bot.add_cog(AdminCog(bot))
