"""Elo service."""

from __future__ import annotations

import json

from app.logging import get_logger
from app.repositories.elo_repository import EloRepository
from app.repositories.player_repository import PlayerRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class EloService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.elo_repo = EloRepository(client)
        self.players = PlayerRepository(client)

    async def apply_match_result(
        self,
        guild_id: int,
        players: list[dict],
        *,
        winner_side: str,
        win_delta: int = 8,
        loss_delta: int = -6,
        match_id: int | None = None,
        approved_by: int | None = None,
    ) -> None:
        """Apply Elo changes for all players in a match atomically.

        Delegates to a Postgres function ``apply_match_result`` so that updating
        every player's Elo and writing the Elo transactions happens in a single
        database transaction. Each player row is ``{player_id, elo_before, role_side}``.
        """
        params = {
            "p_guild_id": guild_id,
            "p_players": json.dumps(list(players)),
            "p_winner_side": winner_side,
            "p_win_delta": win_delta,
            "p_loss_delta": loss_delta,
            "p_match_id": match_id,
            "p_approved_by": approved_by,
        }
        await self.client.rpc("apply_match_result", params).execute()
        logger.info(
            "Match Elo applied: match=%s, winner=%s, players=%d",
            match_id,
            winner_side,
            len(players),
        )
