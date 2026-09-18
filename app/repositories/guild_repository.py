"""Guild repository."""

from __future__ import annotations

from typing import Any

from app.logging import get_logger
from app.models.guild import Guild, GuildSettings
from app.repositories.base import BaseRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class GuildRepository(BaseRepository[Guild]):
    model = Guild
    table_name = "guilds"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)
        self.client = client

    async def get_guild(self, guild_id: int) -> Guild | None:
        result = await self._table().select("*").eq("id", guild_id).maybe_single().execute()
        row = self._single_row(result)
        return Guild.from_row(row) if row is not None else None

    async def ensure_guild(self, guild_id: int) -> Guild:
        guild = await self.get_guild(guild_id)
        if guild is None:
            inserted = await self.insert(Guild(id=guild_id, enabled=True))
            guild = inserted if inserted else Guild(id=guild_id, enabled=True)
        return guild

    async def get_settings(self, guild_id: int) -> GuildSettings | None:
        settings_client = self.client.table("guild_settings")
        result = (
            await settings_client.select("*").eq("guild_id", guild_id).maybe_single().execute()
        )
        row = self._single_row(result)
        return GuildSettings.from_row(row) if row is not None else None

    async def list_all_settings(self) -> list[GuildSettings]:
        result = await self.client.table("guild_settings").select("*").execute()
        return [GuildSettings.from_row(row) for row in self._rows(result)]

    async def upsert_settings(self, guild_id: int, **kwargs: Any) -> GuildSettings:
        await self.ensure_guild(guild_id)
        settings = await self.get_settings(guild_id)
        if settings is None:
            settings = GuildSettings(guild_id=guild_id, **kwargs)
            inserted = await self.client.table("guild_settings").insert(
                settings.to_payload()
            ).execute()
            row = self._single_row(inserted)
            if row is not None:
                settings = GuildSettings.from_row(row)
        else:
            payload = {k: v for k, v in kwargs.items()}
            await self.client.table("guild_settings").update(payload).eq(
                "guild_id", guild_id
            ).execute()
            settings = settings.model_copy(update=payload)
        return settings
