"""Leaderboard service."""

from app.repositories.player_repository import PlayerRepository


class LeaderboardService:
    def __init__(self, session):
        self.players = PlayerRepository(session)

    async def get(self, guild_id: int, limit: int = 10):
        return await self.players.get_leaderboard(guild_id, limit)
