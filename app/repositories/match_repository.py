"""Match repository."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.match import Match, MatchPlayer, MatchResult


class MatchRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, match: Match) -> Match:
        self.session.add(match)
        await self.session.flush()
        return match

    async def add_player(self, player: MatchPlayer) -> MatchPlayer:
        self.session.add(player)
        await self.session.flush()
        return player

    async def get(self, match_id: int) -> Match | None:
        return await self.session.get(Match, match_id)

    async def get_by_display_id(self, display_id: str) -> Match | None:
        result = await self.session.execute(select(Match).where(Match.display_id == display_id))
        return result.scalar_one_or_none()

    async def get_active(self, guild_id: int) -> Match | None:
        result = await self.session.execute(
            select(Match).where(
                Match.guild_id == guild_id,
                Match.status.in_(["CREATING", "READY", "IN_PROGRESS"]),
            )
        )
        return result.scalar_one_or_none()

    async def get_players(self, match_id: int) -> Sequence[MatchPlayer]:
        result = await self.session.execute(
            select(MatchPlayer).where(MatchPlayer.match_id == match_id).order_by(MatchPlayer.call_number)
        )
        return list(result.scalars().all())

    async def get_player_count(self, match_id: int) -> int:
        result = await self.session.execute(
            select(MatchPlayer).where(MatchPlayer.match_id == match_id)
        )
        return len(result.all())

    async def update_status(self, match_id: int, status: str) -> None:
        match = await self.get(match_id)
        if match:
            match.status = status
            await self.session.flush()

    async def update_channels(self, match_id: int, text_id: int, voice_id: int) -> None:
        match = await self.get(match_id)
        if match:
            match.text_channel_id = text_id
            match.voice_channel_id = voice_id
            await self.session.flush()

    async def get_next_display_id(self, guild_id: int) -> str:
        result = await self.session.execute(
            select(Match)
            .where(Match.guild_id == guild_id)
            .order_by(Match.id.desc())
            .limit(1)
        )
        last = result.scalar_one_or_none()
        seq = (last.id + 1) if last else 1
        return f"AU-{seq:08d}"

    async def create_result(self, result: MatchResult) -> MatchResult:
        self.session.add(result)
        await self.session.flush()
        return result
