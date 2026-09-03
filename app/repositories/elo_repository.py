"""Elo repository."""

from __future__ import annotations

from collections.abc import Sequence

from app.logging import get_logger
from app.models.elo import EloTransaction
from app.models.player import Player
from app.repositories.base import BaseRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class EloRepository(BaseRepository[EloTransaction]):
    model = EloTransaction
    table_name = "elo_transactions"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)
        self.client = client

    async def create_transaction(self, tx: EloTransaction) -> EloTransaction:
        created = await self.insert(tx)
        return created if created else tx

    async def get_history(self, player_id: int, limit: int = 10) -> Sequence[EloTransaction]:
        result = (
            await self._table()
            .select("*")
            .eq("player_id", player_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return [EloTransaction.from_row(row) for row in result.data or []]

    async def apply_elo_change(
        self,
        player: Player,
        change: int,
        *,
        match_id: int | None = None,
        reason: str = "",
        created_by: int | None = None,
    ) -> EloTransaction:
        old_elo = player.elo
        new_elo = old_elo + change
        new_peak = max(player.peak_elo, new_elo)

        await self.client.table("players").update(
            {"elo": new_elo, "peak_elo": new_peak}
        ).eq("id", player.id).execute()

        tx = EloTransaction(
            guild_id=player.guild_id,
            player_id=player.id,
            match_id=match_id,
            old_elo=old_elo,
            change=change,
            new_elo=new_elo,
            reason=reason,
            created_by=created_by,
        )
        created = await self.create_transaction(tx)
        player.elo = new_elo
        player.peak_elo = new_peak
        return created
