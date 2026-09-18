"""Match service."""

from __future__ import annotations

import json
import random

from app.logging import get_logger
from app.models.guild import GuildSettings
from app.models.match import Match, MatchPlayer
from app.models.player import Player
from app.repositories.guild_repository import GuildRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.player_repository import PlayerRepository
from app.repositories.queue_repository import QueueRepository
from app.utils.constants import (
    MATCH_STATUS_CANCELLED,
    MATCH_STATUS_CREATING,
    MATCH_STATUS_IN_PROGRESS,
    MATCH_STATUS_READY,
)
from supabase import AsyncClient

logger = get_logger(__name__)

ACTIVE_STATUSES = (
    MATCH_STATUS_CREATING,
    MATCH_STATUS_READY,
    MATCH_STATUS_IN_PROGRESS,
)


class MatchService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.match_repo = MatchRepository(client)
        self.players = PlayerRepository(client)
        self.guilds = GuildRepository(client)

    async def get_guild_settings(self, guild_id: int) -> GuildSettings | None:
        return await self.guilds.get_settings(guild_id)

    async def get_player(self, player_id: int) -> Player | None:
        return await self.players.get_by_id(player_id)

    async def claim_from_queue(self, guild_id: int) -> tuple[Match, list[int]] | None:
        """Atomically claim a full guild queue and create its match.

        PostgreSQL owns the queue-size check, row locking, queue deletion, and
        match/player inserts. ``None`` means the guild does not currently have
        enough eligible players; no queue rows are removed in that case.
        """
        data = await self.match_repo.claim_from_queue(guild_id)
        if not data:
            return None
        if not isinstance(data.get("match"), dict):
            raise RuntimeError("claim_match_from_queue RPC returned an invalid payload")

        match = Match.from_row(data["match"])
        player_ids = [int(player_id) for player_id in data.get("player_ids", [])]
        logger.info(
            "Queue claimed and match created: %s (guild=%s, players=%d)",
            match.display_id,
            guild_id,
            len(player_ids),
        )
        return match, player_ids

    async def create_match(self, guild_id: int, player_ids: list[int]) -> Match:
        """Create a match and its players atomically via the ``create_match`` RPC.

        The Postgres function receives the (already shuffled) player ids, inserts
        the match row plus one ``match_players`` row per player with CALL numbers
        and captured Elo, computes the average Elo, and returns the new match.
        """
        shuffled = list(player_ids)
        random.shuffle(shuffled)

        row = await self.match_repo.create_match_from_ids(
            guild_id, json.dumps(shuffled)
        )
        if row:
            match = Match.from_row(row)
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

    async def get_players(self, match_id: int) -> list[MatchPlayer]:
        return list(await self.match_repo.get_players(match_id))

    async def update_channels(self, match_id: int, text_id: int, voice_id: int) -> None:
        await self.match_repo.update_channels(match_id, text_id, voice_id)

    async def set_status(self, match_id: int, status: str) -> None:
        await self.match_repo.update_status(match_id, status)

    async def finalize_provisioning(self, match_id: int, text_id: int, voice_id: int) -> None:
        """Persist both channels and start the match in one row update."""
        await self.match_repo.finalize_provisioning(match_id, text_id, voice_id)

    async def get_active_matches(self, guild_id: int | None = None) -> list[Match]:
        return await self.match_repo.list_active(guild_id)

    async def requeue_players(self, match_id: int) -> None:
        """Return a match's players to the waiting queue (recovery path)."""
        match = await self.match_repo.get(match_id)
        if match is None:
            return
        queue_repo = QueueRepository(self.client)
        players = await self.match_repo.get_players(match_id)
        for match_player in players:
            if await queue_repo.get_entry(match.guild_id, match_player.player_id) is None:
                await queue_repo.add(match.guild_id, match_player.player_id)
        await self.match_repo.update_status(match_id, MATCH_STATUS_CANCELLED)
        logger.info("Match reverted and players requeued: match=%s", match_id)
