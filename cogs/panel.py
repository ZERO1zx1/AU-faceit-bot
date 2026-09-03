import discord
from discord.ext import commands
from database import db

class PanelCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.has_permissions(administrator=True)
    @commands.group(name="panel")
    async def panel(self, ctx):
        await ctx.send("Commands: `create`, `edit`, `delete`")

    @panel.command(name="delete")
    async def panel_delete(self, ctx, panel_type: str):
        settings = await db.get_guild_settings(ctx.guild.id)
        panels = settings.get("panel_messages", {})
        msg_id = panels.get(panel_type)
        if msg_id:
            try:
                msg = await ctx.channel.fetch_message(msg_id)
                await msg.delete()
            except: pass
            panels.pop(panel_type, None)
            await db.upsert_guild_settings({"guild_id": ctx.guild.id, "panel_messages": panels})
            await ctx.send(f"Panel {panel_type} deleted.")

async def setup(bot):
    await bot.add_cog(PanelCog(bot))
