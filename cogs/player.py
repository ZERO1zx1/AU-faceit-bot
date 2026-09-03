import discord
from discord.ext import commands
from database import db
import math

class PlayerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="profile")
    async def profile(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        player = await db.get_player(ctx.guild.id, member.id)
        if not player: return await ctx.send("Бүртгүүлээгүй байна.")

        embed = discord.Embed(title=f"{member.display_name} - Profile", color=discord.Color.gold())
        embed.add_field(name="Among Us", value=player["among_us_name"], inline=True)
        embed.add_field(name="AU Elo", value=player["au_elo"], inline=True)
        embed.add_field(name="Level", value=f"L{player['level']}", inline=True)
        embed.add_field(name="Matches", value=player["total_matches"], inline=True)
        embed.add_field(name="Wins (Imp)", value=player["wins_as_impostor"], inline=True)
        embed.add_field(name="Losses", value=player["losses"], inline=True)
        
        v_min = math.floor(player.get("voice_seconds", 0) / 60)
        embed.add_field(name="Voice Time", value=f"{v_min} min", inline=False)
        
        hist = await db.get_elo_history(ctx.guild.id, member.id)
        if hist:
            trend = "\n".join([f"{h['elo_before']} → {h['elo_after']} ({'+' if h['change']>0 else ''}{h['change']})" for h in hist[::-1]])
            embed.add_field(name="Recent Trend", value=trend, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="unregister")
    async def unregister(self, ctx):
        player = await db.get_player(ctx.guild.id, ctx.author.id)
        if not player: return await ctx.send("Бүртгэлгүй байна.")
        
        await db.delete_player_full(ctx.guild.id, ctx.author.id)
        settings = await db.get_guild_settings(ctx.guild.id)
        ver = ctx.guild.get_role(settings.get("verified_role_id"))
        unv = ctx.guild.get_role(settings.get("unverified_role_id"))
        if ver: await ctx.author.remove_roles(ver)
        if unv: await ctx.author.add_roles(unv)
        
        await db.log_audit(ctx.guild.id, "UNREGISTER", ctx.author.id)
        await ctx.send("✅ Бүх өгөгдөл устгагдлаа.")

async def setup(bot):
    await bot.add_cog(PlayerCog(bot))
