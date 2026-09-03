"""Help cog — !help command listing all available commands."""

import textwrap

import discord
from discord.ext import commands

HELP_TEXT = """
**AU FACEIT Bot — Commands**

`!setup-server` — Set up the server (roles, channels, category).
`!setup-register` — Create the registration panel.
`!setup-faceit-level` — Create level roles (1–10).
`!setup-queue` — Create the queue panel.
`!setup-leaderboard` — Set the leaderboard channel.
`!register` — Register your Among Us name.
`!unregister` — Unregister your account.
`!profile <@user>` — Show your or someone's profile.
`!matches <@user>` — Show a user's match history.
`!queue-status` — Show the current queue.
`!elo <@user>` — Show a user's Elo rating.
`!ban <@user> <reason>` — Ban a player (admin).
`!unban <user>` — Unban a player (admin).
`!elo <wins> <losses>` — Set admin Elo (admin).
`!result <match_id>` — Submit or view a match result.
`!leaderboard` — Show the top 10 players.
`!help` — Show this help message.
"""


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🎮 AU FACEIT Bot — Help",
            description=HELP_TEXT.strip(),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
