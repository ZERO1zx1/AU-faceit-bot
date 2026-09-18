"""Queue service."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

from app.logging import get_logger
from app.models.guild import GuildSettings
from app.models.queue import QueueEntry
from app.repositories.guild_repository import GuildRepository
from app.repositories.match_repository import MatchRepository
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

_DEFAULT_QUEUE_SIZE = 15


def resolve_queue_size(settings: GuildSettings | None, default: int = _DEFAULT_QUEUE_SIZE) -> int:
    """Resolve the effective queue size for a guild's settings.

    ``GuildSettings.queue_size`` wins when set to a sane positive value;
    otherwise the fallback constant is used. Keeps every queue UI/cog on the
    same number so matchmaking, status embeds and claims agree.
    """
    if settings is None:
        return default
    value = settings.queue_size
    if value is None or value < 1:
        return default
    return value


class QueueService:
    def __init__(self, client: AsyncClient, queue_size: int = 15) -> None:
        self.client = client
        self.queue_repo = QueueRepository(client)
        self.players = PlayerRepository(client)
        self.guilds = GuildRepository(client)
        self.matches = MatchRepository(client)
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

    async def get_entries(self, guild_id: int) -> Sequence[QueueEntry]:
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

    async def get_guild_settings(self, guild_id: int) -> GuildSettings | None:
        return await self.guilds.get_settings(guild_id)

    async def _in_active_match(self, guild_id: int, player_id: int) -> bool:
        return await self.matches.has_active_match(
            guild_id, player_id, statuses=_ACTIVE_MATCH_STATUSES
        )

    async def pop_all(self, guild_id: int) -> list[int]:
        """Atomically lock and pop all waiting entries.

        Delegates to a Postgres function so the read-and-clear happens in a
        single transaction, avoiding duplicate match creation under concurrency.
        """
        async with self._lock:
            player_ids = await self.queue_repo.pop_all(guild_id)
            logger.info("Queue popped: guild=%s count=%d", guild_id, len(player_ids))
            return player_ids
