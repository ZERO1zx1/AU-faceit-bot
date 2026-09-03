import discord
from discord.ext import commands
from database import db

class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(administrator=True)
    @commands.command(name="setup-leaderboard")
    async def setup_lb(self, ctx):
        settings = await db.get_guild_settings(ctx.guild.id)
        if not settings: return await ctx.send("Run !setup-server first.")
        
        embed = discord.Embed(title="🏆 Top 10 Leaderboard", color=discord.Color.gold())
        msg = await ctx.send(embed=embed)
        
        panels = settings.get("panel_messages", {})
        panels["leaderboard"] = msg.id
        await db.upsert_guild_settings({"guild_id": ctx.guild.id, "panel_messages": panels})
        await self.update_lb(ctx.guild.id)
        await ctx.send("✅ Leaderboard created!")

    @commands.command(name="leaderboard")
    async def leaderboard(self, ctx):
        await self.update_lb(ctx.guild.id, ctx.channel)

    async def update_lb(self, guild_id, channel=None):
        players = await db.get_verified_players(guild_id)
        embed = discord.Embed(title="🏆 Top 10 Leaderboard", color=discord.Color.gold())
        if not players:
            embed.description = "Тоглогч олдсонгүй."
        else:
            desc = ""
            for i, p in enumerate(players, 1):
                desc += f"**#{i}** <@{p['discord_user_id']}> – {p['au_elo']} Elo (L{p['level']})\n"
            embed.description = desc
        
        if channel: await channel.send(embed=embed)
        else:
            settings = await db.get_guild_settings(guild_id)
            msg_id = settings.get("panel_messages", {}).get("leaderboard")
            if msg_id:
                for ch in self.bot.get_all_channels():
                    if ch.guild and ch.guild.id == guild_id:
                        try:
                            msg = await ch.fetch_message(msg_id)
                            await msg.edit(embed=embed)
                            break
                        except: pass

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
