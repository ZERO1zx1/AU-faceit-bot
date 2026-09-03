"""Panels cog — custom panel management."""

from discord.ext import commands


class PanelsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


async def setup(bot):
    await bot.add_cog(PanelsCog(bot))
