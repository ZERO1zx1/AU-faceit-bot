"""Panel repository."""

from __future__ import annotations

from typing import Any

from app.logging import get_logger
from app.models.panel import Panel
from app.repositories.base import BaseRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class PanelRepository(BaseRepository[Panel]):
    model = Panel
    table_name = "panels"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)
        self.client = client

    async def get(self, guild_id: int, panel_id: int) -> Panel | None:
        result = (
            await self._table()
            .select("*")
            .eq("id", panel_id)
            .eq("guild_id", guild_id)
            .maybe_single()
            .execute()
        )
        row = self._single_row(result)
        return Panel.from_row(row) if row is not None else None

    async def list_for_guild(self, guild_id: int) -> list[Panel]:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .order("id")
            .execute()
        )
        return [Panel.from_row(row) for row in self._rows(result)]

    async def create(self, panel: Panel) -> Panel:
        created = await self.insert(panel)
        return created if created else panel

    async def update_fields(self, panel_id: int, fields: dict[str, Any]) -> None:
        await self._table().update(fields).eq("id", panel_id).execute()

    async def set_message_id(self, panel_id: int, message_id: int) -> None:
        await self.update_fields(panel_id, {"message_id": message_id})

    async def delete(self, guild_id: int, panel_id: int) -> bool:
        result = (
            await self._table().delete().eq("id", panel_id).eq("guild_id", guild_id).execute()
        )
        return len(self._rows(result)) > 0
