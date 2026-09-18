"""Background maintenance tasks started from the bot's setup hook."""

from __future__ import annotations

import asyncio
import contextlib

import discord

from app.logging import get_logger
from app.services.leaderboard_service import LeaderboardService
from app.services.setup_service import SetupService
from app.supabase_client import get_client
from app.ui.embeds import leaderboard_embed

logger = get_logger(__name__)

LEADERBOARD_INTERVAL_SECONDS = 12 * 60


class LeaderboardTask:
    """Refreshes the persisted leaderboard message for every configured guild.

    A single shared loop covers all guilds; the ``_running`` flag guarantees
    that only one instance ever runs even if ``start`` is called twice.
    """

    def __init__(self, bot: discord.Client) -> None:
        self.bot = bot
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run(), name="leaderboard-refresh")
        logger.info("Leaderboard background task started")

    async def _run(self) -> None:
        while self._running:
            try:
                await self.refresh_all()
            except Exception:
                logger.exception("Leaderboard background refresh failed")
            await asyncio.sleep(LEADERBOARD_INTERVAL_SECONDS)

    async def stop(self) -> None:
        self._running = False
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Leaderboard background task stopped")

    async def refresh_all(self) -> None:
        client = get_client()
        settings_list = await SetupService(client).guilds.list_all_settings()
        for settings in settings_list:
            if not settings.leaderboard_channel_id:
                continue
            guild = self.bot.get_guild(settings.guild_id)
            if guild is None:
                continue
            try:
                await self._refresh_guild(guild, settings)
            except discord.HTTPException:
                logger.warning(
                    "Leaderboard refresh failed for guild=%s", settings.guild_id, exc_info=True
                )

    async def _refresh_guild(self, guild: discord.Guild, settings) -> None:
        players = await LeaderboardService(get_client()).get(guild.id, limit=10)
        embed = leaderboard_embed(players, guild_name=guild.name)
        channel = guild.get_channel(settings.leaderboard_channel_id)

        if settings.leaderboard_message_id and channel:
            try:
                message = await channel.fetch_message(settings.leaderboard_message_id)
            except discord.HTTPException:
                message = None
            if message is not None:
                await message.edit(embed=embed)
                return

        if channel is None:
            return
        message = await channel.send(embed=embed)
        await SetupService(get_client()).upsert_settings(
            guild.id,
            leaderboard_channel_id=channel.id,
            leaderboard_message_id=message.id,
        )
