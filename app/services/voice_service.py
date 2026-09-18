"""Voice service."""

from __future__ import annotations

from datetime import UTC, date, datetime

from app.logging import get_logger
from app.models.voice import VoiceSession
from app.repositories.player_repository import PlayerRepository
from app.repositories.voice_repository import VoiceSessionRepository, VoiceTotalRepository
from supabase import AsyncClient

logger = get_logger(__name__)

_STALE_MAX_SECONDS = 30 * 60  # cap crash-recovered duration to 30 minutes


class VoiceService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.sessions = VoiceSessionRepository(client)
        self.totals = VoiceTotalRepository(client)
        self.players = PlayerRepository(client)

    async def start_session(self, guild_id: int, player_id: int, channel_id: int) -> None:
        vs = VoiceSession(guild_id=guild_id, player_id=player_id, channel_id=channel_id)
        await self.sessions.create(vs)
        logger.info("Voice join: guild=%s player=%s", guild_id, player_id)

    async def end_session(self, guild_id: int, player_id: int) -> int:
        vs = await self.sessions.get_open(guild_id, player_id)
        if vs is None:
            return 0

        now = datetime.now(UTC)
        joined_at = vs.joined_at or now
        duration = int((now - joined_at).total_seconds())
        if vs.id is not None:
            await self.sessions.close(vs.id, now, duration)
            await self.totals.add_seconds(guild_id, player_id, date.today(), duration)

        player = await self.players.get_by_id(player_id)
        if player is not None:
            total = int(player.total_voice_seconds or 0)
            await self.players.update(player_id, {"total_voice_seconds": total + duration})

        logger.info("Voice leave: player=%s duration=%ds", player_id, duration)
        return duration

    async def get_open_session(self, guild_id: int, player_id: int) -> VoiceSession | None:
        return await self.sessions.get_open(guild_id, player_id)

    async def close_stale_sessions(self) -> int:
        """Close sessions left open by a crash/restart.

        Any session still open with a join time older than ``now`` is a leaked
        session (the bot was offline so ``on_voice_state_update`` never fired).
        Capping the measured duration at ``_STALE_MAX_SECONDS`` avoids counting
        the whole bot-down window as voice time.
        """
        now = datetime.now(UTC)
        closed = 0
        for vs in await self.sessions.list_open():
            joined = vs.joined_at or now
            duration = min(int((now - joined).total_seconds()), _STALE_MAX_SECONDS)
            if duration <= 0:
                duration = 0
            if vs.id is None:
                continue
            await self.sessions.close(vs.id, now, duration)
            await self.totals.add_seconds(vs.guild_id, vs.player_id, date.today(), duration)
            closed += 1
        if closed:
            logger.info("Voice: closed %d stale session(s) after restart", closed)
        return closed
