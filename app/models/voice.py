"""Voice session and voice totals models."""

from datetime import date, datetime

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class VoiceSession(Base):
    __tablename__ = "voice_sessions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False)

    joined_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    left_at: Mapped[datetime | None] = mapped_column(nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)


class VoiceTotal(Base):
    __tablename__ = "voice_totals"
    __table_args__ = (
        UniqueConstraint("guild_id", "player_id", "bucket_date", name="uq_voice_totals_bucket"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    bucket_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_seconds: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
