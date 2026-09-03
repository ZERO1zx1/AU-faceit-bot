"""Queue repository."""

from collections.abc import Sequence

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.queue import QueueEntry
from app.utils.constants import QUEUE_STATUS_WAITING


class QueueRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_entries(self, guild_id: int) -> Sequence[QueueEntry]:
        result = await self.session.execute(
            select(QueueEntry)
            .where(QueueEntry.guild_id == guild_id, QueueEntry.status == QUEUE_STATUS_WAITING)
            .order_by(QueueEntry.joined_at)
        )
        return list(result.scalars().all())

    async def get_entry(self, guild_id: int, player_id: int) -> QueueEntry | None:
        result = await self.session.execute(
            select(QueueEntry).where(
                QueueEntry.guild_id == guild_id,
                QueueEntry.player_id == player_id,
                QueueEntry.status == QUEUE_STATUS_WAITING,
            )
        )
        return result.scalar_one_or_none()

    async def add(self, guild_id: int, player_id: int) -> QueueEntry:
        entry = QueueEntry(guild_id=guild_id, player_id=player_id, status=QUEUE_STATUS_WAITING)
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def remove(self, guild_id: int, player_id: int) -> bool:
        result = await self.session.execute(
            delete(QueueEntry).where(
                QueueEntry.guild_id == guild_id,
                QueueEntry.player_id == player_id,
                QueueEntry.status == QUEUE_STATUS_WAITING,
            )
        )
        await self.session.flush()
        return result.rowcount > 0

    async def clear(self, guild_id: int) -> None:
        await self.session.execute(
            delete(QueueEntry).where(
                QueueEntry.guild_id == guild_id,
                QueueEntry.status == QUEUE_STATUS_WAITING,
            )
        )
        await self.session.flush()

    async def count(self, guild_id: int) -> int:
        result = await self.session.execute(
            select(QueueEntry.id).where(
                QueueEntry.guild_id == guild_id,
                QueueEntry.status == QUEUE_STATUS_WAITING,
            )
        )
        return len(result.all())
