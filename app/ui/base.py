"""Shared Discord UI components with complete exception logging."""

from __future__ import annotations

import discord

from app.logging import get_logger

logger = get_logger(__name__)


def interaction_details(interaction: discord.Interaction) -> str:
    """Return safe IDs useful for diagnosing an interaction failure."""
    message_id = interaction.message.id if interaction.message else None
    return (
        f"guild_id={interaction.guild_id} channel_id={interaction.channel_id} "
        f"user_id={interaction.user.id} message_id={message_id}"
    )


async def report_ui_error(
    interaction: discord.Interaction,
    error: Exception,
    *,
    component: str,
) -> None:
    logger.error(
        "Discord UI error | component=%s %s",
        component,
        interaction_details(interaction),
        exc_info=(type(error), error, error.__traceback__),
    )
    message = "❌ Алдаа гарлаа. Админ `logs/cogs.txt` файлаас дэлгэрэнгүйг шалгана уу."
    try:
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
        logger.exception("Failed to send UI error response | %s", interaction_details(interaction))


class LoggedView(discord.ui.View):
    """View base class that records button and select failures."""

    async def on_error(
        self,
        interaction: discord.Interaction,
        error: Exception,
        item: discord.ui.Item[discord.ui.View],
    ) -> None:
        custom_id = getattr(item, "custom_id", None)
        await report_ui_error(interaction, error, component=f"view:{custom_id}")


class LoggedModal(discord.ui.Modal):
    """Modal base class that records submission failures."""

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await report_ui_error(interaction, error, component=f"modal:{self.custom_id}")
