"""Player model."""

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class Player(TimestampMixin, Base):
    __tablename__ = "players"
    __table_args__ = (
        UniqueConstraint("guild_id", "discord_user_id", name="uq_players_guild_user"),
        UniqueConstraint("guild_id", "among_us_name", name="uq_players_guild_amongus"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    discord_user_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)

    among_us_name: Mapped[str] = mapped_column(String(100), nullable=False)
    nickname: Mapped[str | None] = mapped_column(Text, nullable=True)

    faceit_player_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    faceit_nickname: Mapped[str | None] = mapped_column(String(100), nullable=True)

    elo: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    peak_elo: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)

    level: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wins: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    losses: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    win_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_win_streak: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    total_voice_seconds: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)

    registered_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
