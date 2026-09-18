"""Ban repository."""

from __future__ import annotations

from app.models.ban import Ban
from app.repositories.base import BaseRepository
from supabase import AsyncClient


class BanRepository(BaseRepository[Ban]):
    model = Ban
    table_name = "bans"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)

    async def create(self, ban: Ban) -> Ban:
        inserted = await self.insert(ban)
        if inserted is None:
            raise RuntimeError("ban insert returned no row")
        return inserted

    async def deactivate_active(self, guild_id: int, player_id: int) -> None:
        result = await (
            self._table()
            .update({"active": False})
            .eq("guild_id", guild_id)
            .eq("player_id", player_id)
            .eq("active", True)
            .execute()
        )
        return result
