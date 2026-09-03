"""Elo repository."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.elo import EloTransaction
from app.models.player import Player


class EloRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_transaction(self, tx: EloTransaction) -> EloTransaction:
        self.session.add(tx)
        await self.session.flush()
        return tx

    async def get_history(self, player_id: int, limit: int = 10) -> Sequence[EloTransaction]:
        result = await self.session.execute(
            select(EloTransaction)
            .where(EloTransaction.player_id == player_id)
            .order_by(EloTransaction.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

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
        player.elo = new_elo
        player.peak_elo = max(player.peak_elo, new_elo)
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
        self.session.add(tx)
        await self.session.flush()
        return tx
