"""Guild and GuildSettings models."""

from typing import Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Guild(TimestampMixin, Base):
    __tablename__ = "guilds"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    settings: Mapped[Optional["GuildSettings"]] = relationship(
        back_populates="guild", uselist=False, cascade="all, delete-orphan"
    )


class GuildSettings(TimestampMixin, Base):
    __tablename__ = "guild_settings"

    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), primary_key=True
    )

    admin_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    moderator_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    registered_role_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    register_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    register_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    queue_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    queue_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    leaderboard_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    leaderboard_message_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    match_category_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    log_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    default_elo: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    win_elo: Mapped[int] = mapped_column(Integer, default=8, nullable=False)
    loss_elo: Mapped[int] = mapped_column(Integer, default=-6, nullable=False)

    queue_size: Mapped[int] = mapped_column(Integer, default=15, nullable=False)
    nickname_format: Mapped[str | None] = mapped_column(Text, nullable=True)

    guild: Mapped[Guild] = relationship(back_populates="settings")
