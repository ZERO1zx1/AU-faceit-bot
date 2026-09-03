"""Player repository."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.player import Player


class PlayerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, guild_id: int, discord_user_id: int) -> Player | None:
        result = await self.session.execute(
            select(Player).where(
                Player.guild_id == guild_id, Player.discord_user_id == discord_user_id
            )
        )
        return result.scalar_one_or_none()

    async def get_by_among_us_name(self, guild_id: int, name: str) -> Player | None:
        result = await self.session.execute(
            select(Player).where(
                Player.guild_id == guild_id, Player.among_us_name == name
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, player_id: int) -> Player | None:
        return await self.session.get(Player, player_id)

    async def get_leaderboard(self, guild_id: int, limit: int = 10) -> Sequence[Player]:
        result = await self.session.execute(
            select(Player)
            .where(Player.guild_id == guild_id, Player.active == True)  # noqa: E712
            .order_by(Player.elo.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(
        self,
        guild_id: int,
        discord_user_id: int,
        among_us_name: str,
        nickname: str | None = None,
        default_elo: int = 1000,
    ) -> Player:
        player = Player(
            guild_id=guild_id,
            discord_user_id=discord_user_id,
            among_us_name=among_us_name,
            nickname=nickname,
            elo=default_elo,
            peak_elo=default_elo,
            level=1,
            active=True,
            banned=False,
        )
        self.session.add(player)
        await self.session.flush()
        return player

    async def delete(self, guild_id: int, discord_user_id: int) -> None:
        player = await self.get(guild_id, discord_user_id)
        if player:
            await self.session.delete(player)
            await self.session.flush()

    async def count(self, guild_id: int) -> int:
        result = await self.session.execute(
            select(Player).where(Player.guild_id == guild_id, Player.active == True)  # noqa: E712
        )
        return len(result.all())
