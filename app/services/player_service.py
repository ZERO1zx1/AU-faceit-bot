"""Player service."""

from collections.abc import Sequence

from app.models.elo import EloTransaction
from app.models.player import Player
from app.repositories.elo_repository import EloRepository
from app.repositories.player_repository import PlayerRepository
from supabase import AsyncClient


class PlayerService:
    def __init__(self, client: AsyncClient) -> None:
        self.players = PlayerRepository(client)
        self.elo_repo = EloRepository(client)

    async def get(self, guild_id: int, user_id: int) -> Player | None:
        return await self.players.get(guild_id, user_id)

    async def get_history(self, player_id: int, limit: int = 20) -> Sequence[EloTransaction]:
        return await self.elo_repo.get_history(player_id, limit=limit)

    async def is_banned(self, guild_id: int, user_id: int) -> bool:
        player = await self.players.get(guild_id, user_id)
        return player.banned if player else True

    async def is_registered(self, guild_id: int, user_id: int) -> bool:
        player = await self.players.get(guild_id, user_id)
        return player is not None and player.active

    async def leaderboard(self, guild_id: int, limit: int = 10) -> list[Player]:
        return await self.players.get_leaderboard(guild_id, limit)
