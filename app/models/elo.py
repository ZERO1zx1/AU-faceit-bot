"""Elo transaction model for audit-safe Elo history."""


from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class EloTransaction(TimestampMixin, Base):
    __tablename__ = "elo_transactions"
    __table_args__ = (
        UniqueConstraint(
            "match_id", "player_id", "transaction_type", name="uq_elo_tx_match_player_type"
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    match_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="SET NULL"), nullable=True
    )

    old_elo: Mapped[int] = mapped_column(Integer, nullable=False)
    change: Mapped[int] = mapped_column(Integer, nullable=False)
    new_elo: Mapped[int] = mapped_column(Integer, nullable=False)

    reason: Mapped[str | None] = mapped_column(String(100), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(32), default="MATCH", nullable=False)

    created_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
