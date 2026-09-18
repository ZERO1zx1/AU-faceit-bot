"""Log service — audit log writing."""

import json
from typing import Any

import discord

from app.logging import get_logger
from app.models.audit import AuditLog
from app.repositories.audit_repository import AuditLogRepository
from app.repositories.guild_repository import GuildRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class LogService:
    def __init__(self, client: AsyncClient, bot: Any | None = None) -> None:
        self.client = client
        self.bot = bot
        self.audit_repo = AuditLogRepository(client)
        self.guilds = GuildRepository(client)

    async def log(
        self,
        guild_id: int,
        action_type: str,
        *,
        actor_id: int | None = None,
        target_entity: str | None = None,
        details: dict | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        entry = AuditLog(
            guild_id=guild_id,
            action_type=action_type,
            actor_id=actor_id,
            target_entity=target_entity,
            details=json.dumps(details) if details else None,
            success=success,
            error_message=error_message,
        )
        await self.audit_repo.create(entry)
        await self._send_to_discord(entry, details)

    async def _send_to_discord(self, entry: AuditLog, details: dict | None) -> None:
        """Send a best-effort visible copy without coupling audit durability to Discord."""
        if self.bot is None:
            return
        settings = await self.guilds.get_settings(entry.guild_id)
        if not settings or not settings.log_channel_id:
            return
        try:
            channel = self.bot.get_channel(settings.log_channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(settings.log_channel_id)
            embed = discord.Embed(
                title=f"{'✅' if entry.success else '❌'} {entry.action_type}",
                color=discord.Color.green() if entry.success else discord.Color.red(),
                timestamp=discord.utils.utcnow(),
            )
            if entry.actor_id:
                embed.add_field(name="Actor", value=f"<@{entry.actor_id}>", inline=True)
            if entry.target_entity:
                embed.add_field(name="Target", value=entry.target_entity[:1024], inline=True)
            if details:
                detail_text = "\n".join(f"**{key}:** {value}" for key, value in details.items())
                embed.add_field(name="Details", value=detail_text[:1024], inline=False)
            if entry.error_message:
                embed.add_field(name="Error", value=entry.error_message[:1024], inline=False)
            await channel.send(embed=embed)
        except Exception:
            logger.exception(
                "Discord audit delivery failed | guild_id=%s action=%s channel_id=%s",
                entry.guild_id,
                entry.action_type,
                settings.log_channel_id,
            )
