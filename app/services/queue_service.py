"""Queue service."""

from __future__ import annotations

import asyncio

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.repositories.player_repository import PlayerRepository
from app.repositories.queue_repository import QueueRepository

logger = get_logger(__name__)


class QueueService:
    def __init__(self, session: AsyncSession, queue_size: int = 15) -> None:
        self.session = session
        self.queue_repo = QueueRepository(session)
        self.players = PlayerRepository(session)
        self.queue_size = queue_size
        self._lock = asyncio.Lock()

    async def join(self, guild_id: int, player_id: int) -> int:
        async with self._lock:
            existing = await self.queue_repo.get_entry(guild_id, player_id)
            if existing:
                raise ValueError("Already in queue")

            player = await self.players.get_by_id(player_id)
            if not player or not player.active:
                raise ValueError("Not registered")
            if player.banned:
                raise ValueError("Banned")

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

    async def pop_all(self, guild_id: int) -> list[int]:
        """Atomically lock and pop all waiting entries."""
        async with self._lock:
            entries = await self.queue_repo.get_entries(guild_id)
            if not entries:
                return []
            player_ids = [e.player_id for e in entries]
            await self.queue_repo.clear(guild_id)
            logger.info("Queue popped: guild=%s count=%d", guild_id, len(player_ids))
            return player_ids
