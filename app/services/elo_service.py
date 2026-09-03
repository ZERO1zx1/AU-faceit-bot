"""Elo service."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.repositories.elo_repository import EloRepository
from app.repositories.player_repository import PlayerRepository

logger = get_logger(__name__)


class EloService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.elo_repo = EloRepository(session)
        self.players = PlayerRepository(session)

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

        players: list of dicts with keys { player_id, elo_before, role_side }
        """
        changes = []
        for p in players:
            delta = win_delta if p["role_side"] == winner_side else loss_delta
            player = await self.players.get_by_id(p["player_id"])
            if player is None:
                raise ValueError(f"Player {p['player_id']} not found")
            changes.append((player, delta))

        for player, delta in changes:
            await self.elo_repo.apply_elo_change(
                player,
                delta,
                match_id=match_id,
                reason=f"Match {winner_side}",
                created_by=approved_by,
            )

        await self.session.commit()
        logger.info(
            "Match Elo applied: match=%s, winner=%s, players=%d",
            match_id,
            winner_side,
            len(changes),
        )
