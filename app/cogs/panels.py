"""Panels cog — custom panel create/edit/delete/list management (slash only)."""

import contextlib

import discord
from discord import app_commands
from discord.ext import commands

from app.models.panel import Panel
from app.services.log_service import LogService
from app.services.panel_service import PanelService
from app.supabase_client import get_client
from app.ui.panel_builder import EmbedValidationError, PanelEmbedBuilder, parse_color


async def _send_embed(panel: Panel, channel: discord.TextChannel) -> discord.Message:
    builder = PanelEmbedBuilder.from_panel(panel)
    builder.validate()
    return await channel.send(embed=builder.build())


async def _edit_embed(panel: Panel, guild: discord.Guild) -> bool:
    if not panel.channel_id or not panel.message_id:
        return False
    channel = guild.get_channel(panel.channel_id)
    if not isinstance(channel, discord.TextChannel):
        return False
    try:
        message = await channel.fetch_message(panel.message_id)
    except discord.HTTPException:
        return False
    builder = PanelEmbedBuilder.from_panel(panel)
    builder.validate()
    await message.edit(embed=builder.build())
    return True


class PanelsCog(commands.Cog):
    panel = app_commands.Group(
        name="panel",
        description="Custom panel create/edit/delete/list удирдах.",
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @panel.command(name="create", description="Custom embed panel үүсгэж байрлуулах.")
    @app_commands.describe(
        channel="Panel байрлуулах text channel.",
        title="Panel гарчиг.",
        description="Panel дэлгэрэнгүй текст (нэмэлт).",
        color="Hex color (#RRGGBB), нэмэлт.",
        footer="Footer текст, нэмэлт.",
        image="Зурагны http(s) URL, нэмэлт.",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def panel_create(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel,
        title: str,
        description: str | None = None,
        color: str | None = None,
        footer: str | None = None,
        image: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        client = get_client()
        try:
            parsed_color = parse_color(color) if color else None
        except EmbedValidationError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        panel = Panel(
            guild_id=guild.id,
            type="custom",
            channel_id=channel.id,
            title=title,
            description=description,
            color=parsed_color,
            footer=footer,
            image_url=image,
        )

        try:
            message = await _send_embed(panel, channel)
        except EmbedValidationError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return

        svc = PanelService(client)
        try:
            created = await svc.create(panel)
        except Exception:
            with contextlib.suppress(discord.HTTPException):
                await message.delete()
            raise
        if created.id:
            await svc.set_message_id(created.id, message.id)

        await LogService(client, self.bot).log(
            guild.id,
            "PANEL_CREATE",
            actor_id=interaction.user.id,
            target_entity=created.type or "custom",
            details={"title": title, "channel_id": channel.id, "panel_id": created.id},
        )
        await interaction.followup.send(
            f"✅ Panel created: {message.jump_url}", ephemeral=True
        )

    @panel.command(name="edit", description="Одоо байгаа custom panel-ийг засах.")
    @app_commands.describe(
        panel_id="Panel ID (Panel list командаас харна).",
        title="Шинэ гарчиг бичихэд солигдоно (нэмэлт).",
        description="Шинэ дэлгэрэнгүй текст (нэмэлт).",
        color="Шинэ hex color (нэмэлт).",
        footer="Шинэ footer текст (нэмэлт).",
        image="Шинэ зурагны URL (нэмэлт).",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def panel_edit(
        self,
        interaction: discord.Interaction,
        panel_id: int,
        title: str | None = None,
        description: str | None = None,
        color: str | None = None,
        footer: str | None = None,
        image: str | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        client = get_client()
        svc = PanelService(client)
        panel = await svc.get(guild.id, panel_id)
        if panel is None:
            await interaction.followup.send("Panel олдсонгүй.", ephemeral=True)
            return

        fields: dict[str, object] = {}
        if title is not None:
            fields["title"] = title
        if description is not None:
            fields["description"] = description
        if footer is not None:
            fields["footer"] = footer
        if image is not None:
            fields["image_url"] = image
        if color is not None:
            try:
                fields["color"] = parse_color(color)
            except EmbedValidationError as e:
                await interaction.followup.send(str(e), ephemeral=True)
                return

        try:
            updated = await svc.update(guild.id, panel_id, fields)
        except EmbedValidationError as e:
            await interaction.followup.send(str(e), ephemeral=True)
            return
        if updated is None:
            await interaction.followup.send("Panel олдсонгүй.", ephemeral=True)
            return

        try:
            await _edit_embed(updated, guild)
        except EmbedValidationError as e:
            await interaction.followup.send(
                f"DB шинэчлэгдсэн ч embed буруу: {e}", ephemeral=True
            )
            return

        await LogService(client, self.bot).log(
            guild.id,
            "PANEL_EDIT",
            actor_id=interaction.user.id,
            target_entity=str(panel_id),
            details={"field_keys": sorted(fields.keys())},
        )
        await interaction.followup.send(f"✅ Panel {panel_id} засагдлаа.", ephemeral=True)

    @panel.command(name="delete", description="Custom panel устгах.")
    @app_commands.describe(panel_id="Устгах panel ID.")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel_delete(self, interaction: discord.Interaction, panel_id: int) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        client = get_client()
        svc = PanelService(client)
        panel = await svc.get(guild.id, panel_id)
        if panel is None:
            await interaction.followup.send("Panel олдсонгүй.", ephemeral=True)
            return

        if panel.message_id:
            channel = guild.get_channel(panel.channel_id) if panel.channel_id else None
            if isinstance(channel, discord.TextChannel):
                try:
                    msg = await channel.fetch_message(panel.message_id)
                    await msg.delete()
                except discord.HTTPException:
                    pass

        deleted = await svc.delete(guild.id, panel_id)
        if not deleted:
            await interaction.followup.send("Panel олдсонгүй.", ephemeral=True)
            return

        await LogService(client, self.bot).log(
            guild.id,
            "PANEL_DELETE",
            actor_id=interaction.user.id,
            target_entity=str(panel_id),
            details={"title": panel.title},
        )
        await interaction.followup.send("✅ Panel deleted.", ephemeral=True)

    @panel.command(name="list", description="Серверийн бүх custom panel-ыг жагсаах.")
    @app_commands.checks.has_permissions(administrator=True)
    async def panel_list(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        panels = await PanelService(get_client()).list_for_guild(guild.id)
        if not panels:
            await interaction.followup.send("Panel байхгүй байна.", ephemeral=True)
            return
        lines = [
            f"**#{p.id}** — {p.title or '(no title)'} ({p.type}) "
            f"<#{p.channel_id}>" if p.channel_id else f"**#{p.id}** — {p.title or '(no title)'}"
            for p in panels
        ]
        embed = discord.Embed(
            title="Custom panels",
            description="\n".join(lines),
            color=discord.Color.blurple(),
        )
        await interaction.followup.send(embed=embed, ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(PanelsCog(bot))
