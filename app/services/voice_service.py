"""Voice service."""

from __future__ import annotations

from datetime import UTC, datetime

from app.logging import get_logger
from app.models.voice import VoiceSession
from supabase import AsyncClient

logger = get_logger(__name__)


class VoiceService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def start_session(self, guild_id: int, player_id: int, channel_id: int) -> None:
        vs = VoiceSession(guild_id=guild_id, player_id=player_id, channel_id=channel_id)
        await self.client.table("voice_sessions").insert(vs.to_payload()).execute()
        logger.info("Voice join: guild=%s player=%s", guild_id, player_id)

    async def end_session(self, guild_id: int, player_id: int) -> int:
        result = (
            await self.client.table("voice_sessions")
            .select("*")
            .eq("guild_id", guild_id)
            .eq("player_id", player_id)
            .is_("left_at", None)
            .order("joined_at", desc=True)
            .limit(1)
            .execute()
        )
        rows = result.data or []
        if not rows:
            return 0

        vs = VoiceSession.from_row(rows[0])
        now = datetime.now(UTC)
        joined_at = vs.joined_at or now
        duration = int((now - joined_at).total_seconds())
        if vs.id is not None:
            await self.client.table("voice_sessions").update(
                {"left_at": now.isoformat(), "duration_seconds": duration}
            ).eq("id", vs.id).execute()

        player_res = (
            await self.client.table("players")
            .select("total_voice_seconds")
            .eq("id", player_id)
            .maybe_single()
            .execute()
        )
        if player_res.data:
            total = int(player_res.data.get("total_voice_seconds") or 0)
            await self.client.table("players").update(
                {"total_voice_seconds": total + duration}
            ).eq("id", player_id).execute()

        logger.info("Voice leave: player=%s duration=%ds", player_id, duration)
        return duration
