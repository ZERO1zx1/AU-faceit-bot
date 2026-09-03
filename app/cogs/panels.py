"""Panels cog — custom panel create/edit/delete management."""

import json

import discord
from discord.ext import commands

from app.models.panel import Panel
from app.services.log_service import LogService
from app.supabase_client import get_client


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
        client = get_client()
        panel = Panel(
            guild_id=ctx.guild.id,
            type=panel_type,
            channel_id=channel.id,
            title=title,
            configuration_json=json.dumps({}),
        )
        inserted = await client.table("panels").insert(panel.to_payload()).execute()
        panel_id = (inserted.data or [{}])[0].get("id")

        log_svc = LogService(client)
        await log_svc.log(
            ctx.guild.id, "PANEL_CREATE",
            actor_id=ctx.author.id, target_entity=panel_type,
            details={"title": title, "channel_id": channel.id},
        )

        embed = discord.Embed(
            title=title, description="Panel created.", color=discord.Color.blurple()
        )
        msg = await channel.send(embed=embed)

        if panel_id:
            await client.table("panels").update({"message_id": msg.id}).eq(
                "id", panel_id
            ).execute()

        await ctx.send(f"✅ Panel `{panel_type}` created in {channel.mention}.")

    @panel.command(name="delete")
    @commands.has_permissions(administrator=True)
    async def panel_delete(self, ctx: commands.Context, panel_id: int):
        client = get_client()
        result = (
            await client.table("panels").select("*").eq("id", panel_id).maybe_single().execute()
        )
        if not result.data:
            return await ctx.send("Panel not found.")
        panel = Panel.from_row(result.data)
        if panel.message_id:
            channel = ctx.guild.get_channel(panel.channel_id) if panel.channel_id else None
            if channel:
                try:
                    msg = await channel.fetch_message(panel.message_id)
                    await msg.delete()
                except discord.HTTPException:
                    pass
        await client.table("panels").delete().eq("id", panel_id).execute()
        await ctx.send("✅ Panel deleted.")


async def setup(bot):
    await bot.add_cog(PanelsCog(bot))
