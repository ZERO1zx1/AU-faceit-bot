"""Level role repository."""

from __future__ import annotations

from app.logging import get_logger
from app.models.level import LevelRole
from app.repositories.base import BaseRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class LevelRepository(BaseRepository[LevelRole]):
    model = LevelRole
    table_name = "level_roles"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)
        self.client = client

    async def get_map(self, guild_id: int) -> dict[int, LevelRole]:
        result = (
            await self._table().select("*").eq("guild_id", guild_id).execute()
        )
        return {LevelRole.from_row(row).level: LevelRole.from_row(row) for row in result.data or []}

    async def upsert(
        self,
        guild_id: int,
        level: int,
        *,
        min_elo: int | None = None,
        max_elo: int | None = None,
        role_id: int | None = None,
    ) -> LevelRole:
        existing = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .eq("level", level)
            .maybe_single()
            .execute()
        )
        payload = {
            "guild_id": guild_id,
            "level": level,
            "min_elo": min_elo,
            "max_elo": max_elo,
            "role_id": role_id,
        }
        if existing.data and existing.data.get("id") is not None:
            await self._table().update(payload).eq("id", existing.data["id"]).execute()
            return LevelRole.from_row({**existing.data, **payload})
        result = await self._table().insert(payload).execute()
        if result.data:
            return LevelRole.from_row(result.data[0])
        return LevelRole(
            guild_id=guild_id,
            level=level,
            min_elo=min_elo,
            max_elo=max_elo,
            role_id=role_id,
        )
