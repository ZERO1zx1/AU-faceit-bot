"""Queue entry model."""

from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class QueueEntry(Base):
    __tablename__ = "queue_entries"
    __table_args__ = (
        UniqueConstraint("guild_id", "player_id", "status", name="uq_queue_guild_player"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    joined_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    queue_position: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="WAITING", nullable=False)
