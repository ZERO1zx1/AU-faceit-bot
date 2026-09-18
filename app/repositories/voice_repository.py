"""Voice session repository."""

from __future__ import annotations

from datetime import date, datetime

from app.logging import get_logger
from app.models.voice import VoiceSession, VoiceTotal
from app.repositories.base import BaseRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class VoiceSessionRepository(BaseRepository[VoiceSession]):
    model = VoiceSession
    table_name = "voice_sessions"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)

    async def create(self, session: VoiceSession) -> None:
        await self._table().insert(session.to_payload()).execute()

    async def get_open(self, guild_id: int, player_id: int) -> VoiceSession | None:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .eq("player_id", player_id)
            .is_("left_at", None)
            .order("joined_at", desc=True)
            .limit(1)
            .execute()
        )
        row = self._single_row(result)
        return VoiceSession.from_row(row) if row is not None else None

    async def list_open(self) -> list[VoiceSession]:
        result = await self._table().select("*").is_("left_at", None).execute()
        return [VoiceSession.from_row(row) for row in self._rows(result)]

    async def close(self, session_id: int, left_at: datetime, duration: int) -> None:
        await self._table().update(
            {"left_at": left_at.isoformat(), "duration_seconds": duration}
        ).eq("id", session_id).execute()


class VoiceTotalRepository(BaseRepository[VoiceTotal]):
    model = VoiceTotal
    table_name = "voice_totals"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)

    async def add_seconds(
        self, guild_id: int, player_id: int, bucket_date: date, seconds: int
    ) -> None:
        today = bucket_date or date.today()
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .eq("player_id", player_id)
            .eq("bucket_date", today.isoformat())
            .maybe_single()
            .execute()
        )
        row = self._single_row(result)
        if row is not None and row.get("id") is not None:
            await self._table().update(
                {"total_seconds": int(row.get("total_seconds") or 0) + seconds}
            ).eq("id", row["id"]).execute()
        else:
            await self._table().insert(
                VoiceTotal(
                    guild_id=guild_id,
                    player_id=player_id,
                    bucket_date=today,
                    total_seconds=seconds,
                ).to_payload()
            ).execute()
        return None
