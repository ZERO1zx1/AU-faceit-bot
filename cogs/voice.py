import discord
from discord.ext import commands
from database import db

class VoiceCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if member.bot: return
        if before.channel and before.channel.name.startswith("match-") and (not after.channel or after.channel.id != before.channel.id):
            await db.end_voice_session(member.guild.id, member.id, before.channel.id)
        
        if after.channel and after.channel.name.startswith("match-") and (not before.channel or before.channel.id != after.channel.id):
            await db.start_voice_session(member.guild.id, member.id, after.channel.id)

async def setup(bot):
    await bot.add_cog(VoiceCog(bot))
