"""Player service."""

from app.models.player import Player
from app.repositories.player_repository import PlayerRepository


class PlayerService:
    def __init__(self, session):
        self.players = PlayerRepository(session)

    async def get(self, guild_id: int, user_id: int) -> Player | None:
        return await self.players.get(guild_id, user_id)

    async def is_banned(self, guild_id: int, user_id: int) -> bool:
        player = await self.players.get(guild_id, user_id)
        return player.banned if player else True

    async def is_registered(self, guild_id: int, user_id: int) -> bool:
        player = await self.players.get(guild_id, user_id)
        return player is not None and player.active

    async def leaderboard(self, guild_id: int, limit: int = 10):
        return await self.players.get_leaderboard(guild_id, limit)
