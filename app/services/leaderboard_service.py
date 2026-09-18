"""Leaderboard service — sorting by elo, level, or voice time."""

from app.repositories.player_repository import PlayerRepository
from supabase import AsyncClient

SORT_FIELDS = {
    "elo": "elo",
    "level": "level",
    "voice": "total_voice_seconds",
}


class LeaderboardService:
    def __init__(self, client: AsyncClient):
        self.players = PlayerRepository(client)

    async def get(self, guild_id: int, limit: int = 10, sort_by: str = "elo"):
        column = SORT_FIELDS.get(sort_by, "elo")
        return await self.players.get_leaderboard(guild_id, limit, sort_by=column)
