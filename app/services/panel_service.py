"""Custom panel service — create/edit/delete persistent panels."""

from __future__ import annotations

from typing import Any

from app.logging import get_logger
from app.models.panel import Panel
from app.repositories.panel_repository import PanelRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class PanelService:
    def __init__(self, client: AsyncClient) -> None:
        self.panels = PanelRepository(client)

    async def create(self, panel: Panel) -> Panel:
        return await self.panels.create(panel)

    async def get(self, guild_id: int, panel_id: int) -> Panel | None:
        return await self.panels.get(guild_id, panel_id)

    async def list_for_guild(self, guild_id: int) -> list[Panel]:
        return await self.panels.list_for_guild(guild_id)

    async def update(self, guild_id: int, panel_id: int, fields: dict[str, Any]) -> Panel | None:
        panel = await self.panels.get(guild_id, panel_id)
        if panel is None:
            return None
        await self.panels.update_fields(panel_id, fields)
        return panel.model_copy(update=fields)

    async def set_message_id(self, panel_id: int, message_id: int) -> None:
        await self.panels.set_message_id(panel_id, message_id)

    async def delete(self, guild_id: int, panel_id: int) -> bool:
        return await self.panels.delete(guild_id, panel_id)
