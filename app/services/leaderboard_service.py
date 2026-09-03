"""Leaderboard service."""

from app.repositories.player_repository import PlayerRepository
from supabase import AsyncClient


class LeaderboardService:
    def __init__(self, client: AsyncClient):
        self.players = PlayerRepository(client)

    async def get(self, guild_id: int, limit: int = 10):
        return await self.players.get_leaderboard(guild_id, limit)
