"""Queue service."""

from __future__ import annotations

import asyncio

from app.logging import get_logger
from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.repositories.queue_repository import QueueRepository
from app.utils.constants import (
    MATCH_STATUS_CREATING,
    MATCH_STATUS_IN_PROGRESS,
    MATCH_STATUS_READY,
    MATCH_STATUS_RESULT_PENDING,
)
from supabase import AsyncClient

logger = get_logger(__name__)

_ACTIVE_MATCH_STATUSES = (
    MATCH_STATUS_CREATING,
    MATCH_STATUS_READY,
    MATCH_STATUS_IN_PROGRESS,
    MATCH_STATUS_RESULT_PENDING,
)


class QueueService:
    def __init__(self, client: AsyncClient, queue_size: int = 15) -> None:
        self.client = client
        self.queue_repo = QueueRepository(client)
        self.players = PlayerRepository(client)
        self.guilds = GuildRepository(client)
        self.queue_size = queue_size
        self._lock = asyncio.Lock()

    async def join(self, guild_id: int, player_id: int) -> int:
        async with self._lock:
            existing = await self.queue_repo.get_entry(guild_id, player_id)
            if existing:
                raise ValueError("Та аль хэдийн queue-д байна.")

            player = await self.players.get_by_id(player_id)
            if not player or player.guild_id != guild_id or not player.active:
                raise ValueError("Та эхлээд бүртгүүлэх шаардлагатай.")
            if player.banned:
                raise ValueError("Та хориглогдсон байна.")

            if await self._in_active_match(guild_id, player_id):
                raise ValueError("Та идэвхтэй match-д байна.")

            await self.queue_repo.add(guild_id, player_id)
            count = await self.queue_repo.count(guild_id)
            logger.info("Queue join: guild=%s player=%s count=%d", guild_id, player_id, count)
            return count

    async def leave(self, guild_id: int, player_id: int) -> None:
        async with self._lock:
            removed = await self.queue_repo.remove(guild_id, player_id)
            if removed:
                logger.info("Queue leave: guild=%s player=%s", guild_id, player_id)

    async def count(self, guild_id: int) -> int:
        return await self.queue_repo.count(guild_id)

    async def is_full(self, guild_id: int) -> bool:
        return await self.count(guild_id) >= self.queue_size

    async def get_entries(self, guild_id: int):
        return await self.queue_repo.get_entries(guild_id)

    async def get_status(self, guild_id: int) -> tuple[int, int]:
        """Return ``(count, average_elo)`` for a guild's waiting queue."""
        entries = await self.queue_repo.get_entries(guild_id)
        if not entries:
            return 0, 0
        player_ids = [entry.player_id for entry in entries]
        players = await self.players.get_many_by_ids(guild_id, player_ids)
        total = sum(player.elo for player in players)
        return len(entries), total // len(entries)

    async def get_guild_settings(self, guild_id: int):
        return await self.guilds.get_settings(guild_id)

    async def _in_active_match(self, guild_id: int, player_id: int) -> bool:
        match_rows = (
            await self.client.table("match_players")
            .select("match_id")
            .eq("player_id", player_id)
            .execute()
        )
        match_ids = [row["match_id"] for row in (match_rows.data or [])]
        if not match_ids:
            return False
        active = (
            await self.client.table("matches")
            .select("id")
            .eq("guild_id", guild_id)
            .in_("id", match_ids)
            .in_("status", list(_ACTIVE_MATCH_STATUSES))
            .execute()
        )
        return bool(active.data)

    async def pop_all(self, guild_id: int) -> list[int]:
        """Atomically lock and pop all waiting entries.

        Delegates to a Postgres function so the read-and-clear happens in a
        single transaction, avoiding duplicate match creation under concurrency.
        """
        async with self._lock:
            result = await self.client.rpc("pop_queue_entries", {"p_guild_id": guild_id}).execute()
            player_ids = [int(r) for r in (result.data or [])]
            logger.info("Queue popped: guild=%s count=%d", guild_id, len(player_ids))
            return player_ids
