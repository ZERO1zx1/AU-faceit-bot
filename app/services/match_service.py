"""Match service."""

from __future__ import annotations

import random

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.match import Match, MatchPlayer
from app.repositories.match_repository import MatchRepository
from app.repositories.player_repository import PlayerRepository
from app.utils.constants import MATCH_STATUS_CREATING

logger = get_logger(__name__)


class MatchService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.match_repo = MatchRepository(session)
        self.players = PlayerRepository(session)

    async def create_match(self, guild_id: int, player_ids: list[int]) -> Match:
        display_id = await self.match_repo.get_next_display_id(guild_id)
        match = Match(
            guild_id=guild_id,
            display_id=display_id,
            status=MATCH_STATUS_CREATING,
        )
        await self.match_repo.create(match)

        shuffled = list(player_ids)
        random.shuffle(shuffled)
        elo_sum = 0
        for idx, pid in enumerate(shuffled, start=1):
            player = await self.players.get_by_id(pid)
            elo = player.elo if player else 1000
            elo_sum += elo
            mp = MatchPlayer(
                match_id=match.id,
                player_id=pid,
                call_number=idx,
                elo_before=elo,
            )
            await self.match_repo.add_player(mp)

        match.average_elo = elo_sum // len(player_ids) if player_ids else 0
        await self.session.commit()
        logger.info(
            "Match created: %s (guild=%s, players=%d)",
            display_id, guild_id, len(player_ids),
        )
        return match

    async def get_match(self, match_id: int) -> Match | None:
        return await self.match_repo.get(match_id)

    async def get_active(self, guild_id: int) -> Match | None:
        return await self.match_repo.get_active(guild_id)

    async def get_players(self, match_id: int) -> list[MatchPlayer]:
        return list(await self.match_repo.get_players(match_id))

    async def update_channels(self, match_id: int, text_id: int, voice_id: int):
        await self.match_repo.update_channels(match_id, text_id, voice_id)
        await self.session.commit()

    async def set_status(self, match_id: int, status: str):
        await self.match_repo.update_status(match_id, status)
        await self.session.commit()
