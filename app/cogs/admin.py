"""Admin cog — /player elo, /player ban, /player unban, /match cancel."""

import discord
from discord.ext import commands

from app.models.ban import Ban
from app.repositories.player_repository import PlayerRepository
from app.services.log_service import LogService
from app.supabase_client import get_client


class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="elo")
    @commands.has_permissions(manage_guild=True)
    async def elo(self, ctx: commands.Context, member: discord.Member, amount: int):
        client = get_client()
        repo = PlayerRepository(client)
        player = await repo.get(ctx.guild.id, member.id)
        if not player:
            return await ctx.send("Player not found.")
        old_elo = player.elo
        new_elo = old_elo + amount
        new_peak = max(player.peak_elo, new_elo)
        await repo.update(player.id, {"elo": new_elo, "peak_elo": new_peak})
        log_svc = LogService(client)
        await log_svc.log(
            ctx.guild.id, "ELO_MANUAL",
            actor_id=ctx.author.id,
            target_entity=member.display_name,
            details={"old": old_elo, "new": new_elo, "delta": amount},
        )
        await ctx.send(f"✅ {member.mention} Elo: {old_elo} → {new_elo}")

    @commands.command(name="ban")
    @commands.has_permissions(manage_guild=True)
    async def ban(
        self, ctx: commands.Context, member: discord.Member, *, reason: str = "No reason"
    ):
        client = get_client()
        repo = PlayerRepository(client)
        player = await repo.get(ctx.guild.id, member.id)
        if not player:
            return await ctx.send("Player not found.")
        await repo.update(player.id, {"banned": True})
        ban = Ban(
            guild_id=ctx.guild.id, player_id=player.id,
            reason=reason, banned_by=ctx.author.id,
        )
        await client.table("bans").insert(ban.to_payload()).execute()
        log_svc = LogService(client)
        await log_svc.log(
            ctx.guild.id, "BAN", actor_id=ctx.author.id,
            target_entity=member.display_name, details={"reason": reason},
        )
        await ctx.send(f"🔨 {member.mention} banned: {reason}")

    @commands.command(name="unban")
    @commands.has_permissions(manage_guild=True)
    async def unban(self, ctx: commands.Context, member: discord.Member):
        client = get_client()
        repo = PlayerRepository(client)
        player = await repo.get(ctx.guild.id, member.id)
        if not player:
            return await ctx.send("Player not found.")
        await repo.update(player.id, {"banned": False})
        await (
            client.table("bans")
            .update({"active": False})
            .eq("player_id", player.id)
            .eq("active", True)
            .execute()
        )
        await ctx.send(f"✅ {member.mention} unbanned")
