"""Queue repository."""

from __future__ import annotations

from collections.abc import Sequence

from app.logging import get_logger
from app.models.queue import QueueEntry
from app.repositories.base import BaseRepository
from app.utils.constants import QUEUE_STATUS_WAITING
from supabase import AsyncClient

logger = get_logger(__name__)


class QueueRepository(BaseRepository[QueueEntry]):
    model = QueueEntry
    table_name = "queue_entries"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)
        self.client = client

    async def get_entries(self, guild_id: int) -> Sequence[QueueEntry]:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .eq("status", QUEUE_STATUS_WAITING)
            .order("joined_at")
            .execute()
        )
        return [QueueEntry.from_row(row) for row in self._rows(result)]

    async def get_entry(self, guild_id: int, player_id: int) -> QueueEntry | None:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .eq("player_id", player_id)
            .eq("status", QUEUE_STATUS_WAITING)
            .maybe_single()
            .execute()
        )
        return QueueEntry.from_row(result.data) if result.data else None

    async def add(self, guild_id: int, player_id: int) -> QueueEntry:
        entry = QueueEntry(guild_id=guild_id, player_id=player_id, status=QUEUE_STATUS_WAITING)
        created = await self.insert(entry)
        return created if created else entry

    async def remove(self, guild_id: int, player_id: int) -> bool:
        result = (
            await self._table()
            .delete()
            .eq("guild_id", guild_id)
            .eq("player_id", player_id)
            .eq("status", QUEUE_STATUS_WAITING)
            .execute()
        )
        return len(self._rows(result)) > 0

    async def clear(self, guild_id: int) -> None:
        await (
            self._table().delete().eq("guild_id", guild_id).eq("status", QUEUE_STATUS_WAITING).execute()
        )

    async def count(self, guild_id: int) -> int:
        result = (
            await self._table()
            .select("id")
            .eq("guild_id", guild_id)
            .eq("status", QUEUE_STATUS_WAITING)
            .execute()
        )
        return len(self._rows(result))
