"""Help cog — !help command listing all available commands."""

import discord
from discord.ext import commands

FIELDS = [
    ("⚙️ Setup", [
        ("`!setup-server`", "Set up the server (roles, channels, category)"),
        ("`!setup-register`", "Create the registration panel"),
        ("`!setup-faceit-level`", "Create level roles (1–10)"),
        ("`!setup-queue`", "Create the queue panel"),
        ("`!setup-leaderboard`", "Set the leaderboard channel"),
    ]),
    ("👤 Profile", [
        ("`!register`", "Register your Among Us name"),
        ("`!unregister`", "Unregister your account"),
        ("`!profile <@user>`", "Show your or someone's profile"),
        ("`!matches <@user>`", "Show a user's match history"),
        ("`!queue-status`", "Show the current queue"),
        ("`!elo <@user>`", "Show a user's Elo rating"),
    ]),
    ("🏆 Match & Results", [
        ("`!result <match_id>`", "Submit or view a match result"),
        ("`!leaderboard`", "Show the top 10 players"),
    ]),
    ("🔧 Admin", [
        ("`!ban <@user> <reason>`", "Ban a player"),
        ("`!unban <user>`", "Unban a player"),
        ("`!elo <wins> <losses>`", "Set admin Elo"),
    ]),
    ("❓ Info", [
        ("`!help`", "Show this help message"),
    ]),
]

HELP_EMBED = (
    "**AU FACEIT Bot — Commands**\n\n"
    "Use the commands below to manage registration, queue, "
    "matches, and leaderboard. Admin commands require administrator permission."
)


class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="help")
    async def help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="🎮 AU FACEIT Bot — Help",
            description=HELP_EMBED,
            color=discord.Color.blurple(),
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild and ctx.guild.icon else ctx.author.display_avatar.url)
        for name, cmds in FIELDS:
            value = "\n".join(f"  {c} — {d}" for c, d in cmds)
            if len(value) > 1024:
                value = value[:1021] + "..."
            embed.add_field(name=name, value=value, inline=False)
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(HelpCog(bot))
