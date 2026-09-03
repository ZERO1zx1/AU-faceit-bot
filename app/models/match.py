"""Match, MatchPlayer and MatchResult models."""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class Match(Base):
    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    display_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True, index=True)

    status: Mapped[str] = mapped_column(String(20), default="CREATING", nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(nullable=True)

    text_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    voice_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    average_elo: Mapped[int | None] = mapped_column(Integer, nullable=True)

    winner_side: Mapped[str | None] = mapped_column(String(20), nullable=True)
    result_submitted_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    result_approved_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    result_processed: Mapped[bool] = mapped_column(default=False, nullable=False)

    players: Mapped[list["MatchPlayer"]] = relationship(
        back_populates="match", cascade="all, delete-orphan"
    )
    result: Mapped[Optional["MatchResult"]] = relationship(
        back_populates="match", uselist=False, cascade="all, delete-orphan"
    )


class MatchPlayer(Base):
    __tablename__ = "match_players"
    __table_args__ = (
        UniqueConstraint("match_id", "player_id", name="uq_match_players_match_player"),
        UniqueConstraint("match_id", "call_number", name="uq_match_players_match_call"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("players.id", ondelete="CASCADE"), nullable=False
    )

    call_number: Mapped[int] = mapped_column(Integer, nullable=False)
    role_side: Mapped[str | None] = mapped_column(String(20), nullable=True)

    elo_before: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elo_delta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    elo_after: Mapped[int | None] = mapped_column(Integer, nullable=True)

    result: Mapped[str | None] = mapped_column(String(20), nullable=True)

    match: Mapped[Match] = relationship(back_populates="players")


class MatchResult(Base):
    __tablename__ = "match_results"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    winner_side: Mapped[str] = mapped_column(String(20), nullable=False)
    screenshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    submitted_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    approved_by: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
    approved_at: Mapped[datetime | None] = mapped_column(nullable=True)

    match: Mapped[Match] = relationship(back_populates="result")


class ResultSubmission(Base):
    __tablename__ = "result_submissions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    match_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    guild_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("guilds.id", ondelete="CASCADE"), nullable=False, index=True
    )
    submitted_by: Mapped[int] = mapped_column(BigInteger, nullable=False)
    winner_side: Mapped[str] = mapped_column(String(20), nullable=False)
    impostor_player_ids: Mapped[str] = mapped_column(Text, nullable=False)
    screenshot_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING", nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(nullable=False, server_default="now()")
