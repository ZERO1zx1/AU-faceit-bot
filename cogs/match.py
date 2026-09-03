import discord
from discord.ext import commands
from database import db
from utils.helpers import is_valid_url
from config import config

class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(administrator=True)
    @commands.command(name="result")
    async def result(self, ctx, match_id: str, imp1: discord.Member, imp2: discord.Member, imp3: discord.Member, url: str, w_elo: int = None, l_elo: int = None):
        match = await db.get_match(match_id)
        if not match or match["status"] != "open":
            return await ctx.send("Match ID буруу эсвэл дууссан байна.")
        
        if not is_valid_url(url): return await ctx.send("URL буруу байна.")
        
        imp_ids = [imp1.id, imp2.id, imp3.id]
        if len(set(imp_ids)) != 3: return await ctx.send("Impostor-ууд өөр байх ёстой.")
        
        roster = await db.get_match_players(match_id)
        r_ids = [p["discord_user_id"] for p in roster]
        for uid in imp_ids:
            if uid not in r_ids: return await ctx.send(f"<@{uid}> roster-д байхгүй.")
        
        w = w_elo if w_elo is not None else config.impostor_elo
        l = l_elo if l_elo is not None else config.crewmate_elo
        crew = [uid for uid in r_ids if uid not in imp_ids]
        
        try:
            await db.apply_result_rpc(match_id, ctx.guild.id, imp_ids, crew, w, l, ctx.author.id, url)
            
            for cid in [match.get("text_channel_id"), match.get("voice_channel_id")]:
                if cid:
                    ch = ctx.guild.get_channel(cid)
                    if ch: await ch.delete()
            
            await ctx.send(f"✅ Match {match_id[:8]} result processed. Channels deleted.")
        except Exception as e:
            await ctx.send(f"RPC Error: {e}")

async def setup(bot):
    await bot.add_cog(MatchCog(bot))
