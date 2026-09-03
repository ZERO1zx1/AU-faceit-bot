"""Match, MatchPlayer, MatchResult and ResultSubmission models."""

from __future__ import annotations

from datetime import datetime

from app.models.base import SupabaseModel


class Match(SupabaseModel):
    """A competitive match between up to ``queue_size`` players."""

    id: int | None = None
    guild_id: int
    display_id: str

    status: str = "CREATING"
    created_at: datetime | None = None
    started_at: datetime | None = None
    finished_at: datetime | None = None

    text_channel_id: int | None = None
    voice_channel_id: int | None = None

    average_elo: int | None = None

    winner_side: str | None = None
    result_submitted_by: int | None = None
    result_approved_by: int | None = None

    result_processed: bool = False


class MatchPlayer(SupabaseModel):
    """A player assigned to a match with a CALL number and role side."""

    id: int | None = None
    match_id: int
    player_id: int

    call_number: int
    role_side: str | None = None

    elo_before: int | None = None
    elo_delta: int | None = None
    elo_after: int | None = None

    result: str | None = None


class MatchResult(SupabaseModel):
    """The final, approved result of a completed match."""

    id: int | None = None
    match_id: int
    winner_side: str
    screenshot_url: str | None = None
    submitted_by: int
    approved_by: int | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None


class ResultSubmission(SupabaseModel):
    """A pending result submission waiting for an admin to approve."""

    id: int | None = None
    match_id: int
    guild_id: int
    submitted_by: int
    winner_side: str
    impostor_player_ids: str
    screenshot_url: str | None = None
    status: str = "PENDING"
    submitted_at: datetime | None = None
    approved_by: int | None = None
    approved_at: datetime | None = None
