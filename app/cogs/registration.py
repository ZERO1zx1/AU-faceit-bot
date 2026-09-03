"""Registration cog — /unregister with confirmation."""

import discord
from discord.ext import commands

from app.services.registration_service import RegistrationService
from app.supabase_client import get_client
from app.ui.views import UnregisterConfirmView


class RegistrationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="unregister")
    async def unregister(self, ctx: commands.Context):
        client = get_client()
        svc = RegistrationService(client)
        player = await svc.get(ctx.guild.id, ctx.author.id)
        if not player:
            return await ctx.send("Та бүртгэлгүй байна.")

        embed = discord.Embed(
            title="⚠️ Unregister",
            description="Та AU FACEIT бүртгэлээ устгахдаа итгэлтэй байна уу?\n\n"
                        "**Note:** Active queue/match-д байвал unregister хийхгүй.",
            color=discord.Color.orange(),
        )
        view = UnregisterConfirmView()
        await ctx.send(embed=embed, view=view)


async def setup(bot):
    await bot.add_cog(RegistrationCog(bot))
