import discord
from discord.ext import commands
from database import db

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(administrator=True)
    @commands.command(name="elo")
    async def elo(self, ctx, action: str, member: discord.Member, amount: int):
        if action not in ["add", "remove"]: return await ctx.send("Use add/remove")
        player = await db.get_player(ctx.guild.id, member.id)
        if not player: return await ctx.send("Player not found.")
        
        change = amount if action == "add" else -amount
        new_elo = player["au_elo"] + change
        await db.update_player_elo(ctx.guild.id, member.id, new_elo)
        await ctx.send(f"✅ {member.display_name} Elo {action} {amount} -> {new_elo}")

    @commands.has_permissions(administrator=True)
    @commands.command(name="logs")
    async def logs(self, ctx, log_type: str = None, page: int = 1):
        res_data = await db.get_audit_logs(ctx.guild.id, log_type, page)
        if not res_data: return await ctx.send("Лог олдсонгүй.")
        
        desc = "\n".join([f"**{l['action_type']}** <@{l['actor_id']}>: {l['details']} ({l['created_at'][:10]})" for l in res_data])
        await ctx.send(embed=discord.Embed(title="Audit Logs", description=desc))

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
