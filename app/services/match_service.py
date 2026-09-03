"""Match service."""

from __future__ import annotations

import json
import random

from app.logging import get_logger
from app.models.match import Match
from app.repositories.match_repository import MatchRepository
from app.repositories.player_repository import PlayerRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class MatchService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.match_repo = MatchRepository(client)
        self.players = PlayerRepository(client)

    async def create_match(self, guild_id: int, player_ids: list[int]) -> Match:
        """Create a match and its players atomically via the ``create_match`` RPC.

        The Postgres function receives the (already shuffled) player ids, inserts
        the match row plus one ``match_players`` row per player with CALL numbers
        and captured Elo, computes the average Elo, and returns the new match.
        """
        shuffled = list(player_ids)
        random.shuffle(shuffled)

        params = {
            "p_guild_id": guild_id,
            "p_player_ids": json.dumps(shuffled),
        }
        res = await self.client.rpc("create_match", params).execute()
        data = res.data if res.data else None
        if isinstance(data, list) and data:
            match = Match.from_row(data[0])
            logger.info(
                "Match created: %s (guild=%s, players=%d)",
                match.display_id, guild_id, len(player_ids),
            )
            return match
        raise RuntimeError("create_match RPC returned no match")

    async def get_match(self, match_id: int) -> Match | None:
        return await self.match_repo.get(match_id)

    async def get_active(self, guild_id: int) -> Match | None:
        return await self.match_repo.get_active(guild_id)

    async def get_players(self, match_id: int) -> list:
        return list(await self.match_repo.get_players(match_id))

    async def update_channels(self, match_id: int, text_id: int, voice_id: int):
        await self.match_repo.update_channels(match_id, text_id, voice_id)

    async def set_status(self, match_id: int, status: str):
        await self.match_repo.update_status(match_id, status)
