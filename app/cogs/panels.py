"""Panels cog — custom panel create/edit/delete management."""

import json

import discord
from discord.ext import commands

from app.db import SessionFactory
from app.models.panel import Panel
from app.services.log_service import LogService


class PanelsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="panel", invoke_without_command=True)
    @commands.has_permissions(administrator=True)
    async def panel(self, ctx: commands.Context):
        await ctx.send("Subcommands: `panel create`, `panel edit`, `panel delete`.")

    @panel.command(name="create")
    @commands.has_permissions(administrator=True)
    async def panel_create(
        self,
        ctx: commands.Context,
        panel_type: str,
        channel: discord.TextChannel,
        title: str,
    ):
        async with SessionFactory() as session:
            panel = Panel(
                guild_id=ctx.guild.id,
                type=panel_type,
                channel_id=channel.id,
                title=title,
                configuration_json=json.dumps({}),
            )
            session.add(panel)
            await session.flush()
            panel_id = panel.id
            log_svc = LogService(session)
            await log_svc.log(
                ctx.guild.id, "PANEL_CREATE",
                actor_id=ctx.author.id, target_entity=panel_type,
                details={"title": title, "channel_id": channel.id},
            )
            await session.commit()

        embed = discord.Embed(
            title=title, description="Panel created.", color=discord.Color.blurple()
        )
        msg = await channel.send(embed=embed)

        async with SessionFactory() as session:
            from sqlalchemy import select
            res = await session.execute(select(Panel).where(Panel.id == panel_id))
            stored = res.scalar_one_or_none()
            if stored:
                stored.message_id = msg.id
            await session.commit()

        await ctx.send(f"✅ Panel `{panel_type}` created in {channel.mention}.")

    @panel.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def panel_delete(self, ctx: commands.Context, panel_id: int):
        async with SessionFactory() as session:
            panel = await session.get(Panel, panel_id)
            if not panel:
                return await ctx.send("Panel not found.")
            if panel.message_id:
                channel = ctx.guild.get_channel(panel.channel_id) if panel.channel_id else None
                if channel:
                    try:
                        msg = await channel.fetch_message(panel.message_id)
                        await msg.delete()
                    except discord.HTTPException:
                        pass
            await session.delete(panel)
            await session.commit()
        await ctx.send("✅ Panel deleted.")


async def setup(bot):
    await bot.add_cog(PanelsCog(bot))
