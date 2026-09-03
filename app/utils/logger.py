"""Logging helpers for Discord embed-based audit logs."""

from datetime import datetime

import discord

from app.logging import get_logger

logger = get_logger(__name__)

_DEFAULT_COLOR = discord.Color.blurple()


async def log_to_discord(bot, guild_id: int, embed: discord.Embed, channel_id: int | None = None):
    ch = channel_id or getattr(bot._guild_log_channels, guild_id, None)
    if not ch:
        return
    try:
        await ch.send(embed=embed)
    except discord.HTTPException:
        logger.warning("Failed to send log to channel %s in guild %s", ch.id, guild_id)


def make_audit_embed(
    action: str,
    *,
    actor: discord.Member | None = None,
    description: str = "",
    fields: dict[str, str] | None = None,
    color: discord.Color = _DEFAULT_COLOR,
    success: bool = True,
) -> discord.Embed:
    embed = discord.Embed(
        title=f"[{action}]",
        description=description,
        color=discord.Color.green() if success else discord.Color.red(),
        timestamp=datetime.utcnow(),
    )
    if actor:
        embed.set_author(name=str(actor), icon_url=actor.display_avatar.url)
    if fields:
        for name, value in fields.items():
            embed.add_field(name=name, value=str(value), inline=False)
    return embed
