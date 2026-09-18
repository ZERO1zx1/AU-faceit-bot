"""Server setup service — guild settings and level role upserts."""

from __future__ import annotations

from app.logging import get_logger
from app.models.guild import GuildSettings
from app.repositories.guild_repository import GuildRepository
from app.services.level_service import LevelService
from supabase import AsyncClient

logger = get_logger(__name__)


class SetupService:
    def __init__(self, client: AsyncClient) -> None:
        self.guilds = GuildRepository(client)
        self.levels = LevelService(client)

    async def get_settings(self, guild_id: int) -> GuildSettings | None:
        return await self.guilds.get_settings(guild_id)

    async def upsert_settings(self, guild_id: int, **kwargs) -> GuildSettings:
        return await self.guilds.upsert_settings(guild_id, **kwargs)

    async def set_level(
        self,
        guild_id: int,
        level: int,
        *,
        min_elo: int | None = None,
        max_elo: int | None = None,
        role_id: int | None = None,
    ):
        return await self.levels.upsert_level(
            guild_id, level, min_elo=min_elo, max_elo=max_elo, role_id=role_id
        )
