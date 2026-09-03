"""Voice service."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.player import Player
from app.models.voice import VoiceSession

logger = get_logger(__name__)


class VoiceService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def start_session(self, guild_id: int, player_id: int, channel_id: int) -> None:
        vs = VoiceSession(
            guild_id=guild_id, player_id=player_id, channel_id=channel_id
        )
        self.session.add(vs)
        await self.session.flush()
        logger.info("Voice join: guild=%s player=%s", guild_id, player_id)

    async def end_session(self, guild_id: int, player_id: int) -> int:
        result = await self.session.execute(
            select(VoiceSession)
            .where(
                VoiceSession.guild_id == guild_id,
                VoiceSession.player_id == player_id,
                VoiceSession.left_at.is_(None),
            )
            .order_by(VoiceSession.joined_at.desc())
            .limit(1)
        )
        vs = result.scalar_one_or_none()
        if not vs:
            return 0

        now = datetime.now(UTC)
        duration = int((now - vs.joined_at).total_seconds())
        vs.left_at = now
        vs.duration_seconds = duration

        player = await self.session.get(Player, vs.player_id)
        if player:
            player.total_voice_seconds += duration

        await self.session.flush()
        logger.info("Voice leave: player=%s duration=%ds", player_id, duration)
        return duration
