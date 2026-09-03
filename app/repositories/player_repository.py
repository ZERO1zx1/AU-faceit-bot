"""Player repository."""

from __future__ import annotations

from app.logging import get_logger
from app.models.player import Player
from app.repositories.base import BaseRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class PlayerRepository(BaseRepository[Player]):
    model = Player
    table_name = "players"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)
        self.client = client

    async def get(self, guild_id: int, discord_user_id: int) -> Player | None:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .eq("discord_user_id", discord_user_id)
            .maybe_single()
            .execute()
        )
        return Player.from_row(result.data) if result.data else None

    async def get_by_among_us_name(self, guild_id: int, name: str) -> Player | None:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .eq("among_us_name", name)
            .maybe_single()
            .execute()
        )
        return Player.from_row(result.data) if result.data else None

    async def get_by_id(self, player_id: int) -> Player | None:
        return await super().get_by_id(player_id)

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> list[Player]:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .eq("active", True)
            .order("elo", desc=True)
            .limit(limit)
            .execute()
        )
        return [Player.from_row(row) for row in self._rows(result)]

    async def create(
        self,
        guild_id: int,
        discord_user_id: int,
        among_us_name: str,
        nickname: str | None = None,
        default_elo: int = 1000,
    ) -> Player:
        player = Player(
            guild_id=guild_id,
            discord_user_id=discord_user_id,
            among_us_name=among_us_name,
            nickname=nickname,
            elo=default_elo,
            peak_elo=default_elo,
            level=1,
            active=True,
            banned=False,
        )
        created = await self.insert(player)
        return created if created else player

    async def delete(self, guild_id: int, discord_user_id: int) -> None:
        await (
            self._table()
            .delete()
            .eq("guild_id", guild_id)
            .eq("discord_user_id", discord_user_id)
            .execute()
        )

    async def update(self, player_id: int, fields: dict) -> Player | None:
        result = await self._table().update(fields).eq("id", player_id).execute()
        if result.data:
            return Player.from_row(result.data[0])
        return None

    async def count(self, guild_id: int) -> int:
        result = await (
            self._table()
            .select("id")
            .eq("guild_id", guild_id)
            .eq("active", True)
            .execute()
        )
        return len(self._rows(result))
