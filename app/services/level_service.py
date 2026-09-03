"""Level service."""

from __future__ import annotations

import discord

from app.logging import get_logger
from app.models.level import LevelRole
from app.models.player import Player
from app.repositories.player_repository import PlayerRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class LevelService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.players = PlayerRepository(client)

    async def get_level_role_map(self, guild_id: int) -> dict[int, LevelRole]:
        result = await self.client.table("level_roles").select("*").eq("guild_id", guild_id).execute()
        return {LevelRole.from_row(row).level: LevelRole.from_row(row) for row in (result.data or [])}

    async def calculate_level(self, guild_id: int, elo: int) -> int:
        levels = await self.get_level_role_map(guild_id)
        for level in sorted(levels.keys(), reverse=True):
            lr = levels[level]
            if lr.min_elo is not None and elo >= lr.min_elo:
                return level
        return 1

    async def update_player_level(self, player: Player) -> int:
        new_level = await self.calculate_level(player.guild_id, player.elo)
        old_level = player.level
        if old_level != new_level and player.id is not None:
            updated = await self.players.update(player.id, {"level": new_level})
            if updated:
                player.level = new_level
            logger.info("Level changed: player=%s %d\u2192%d", player.id, old_level, new_level)
        return new_level

    async def sync_role(
        self, member: discord.Member, old_level: int, new_level: int
    ) -> None:
        levels = await self.get_level_role_map(member.guild.id)
        old_role = levels.get(old_level)
        new_role = levels.get(new_level)
        try:
            if old_role and old_role.role_id:
                role = member.guild.get_role(old_role.role_id)
                if role and role in member.roles:
                    await member.remove_roles(role, reason="Level change")
            if new_role and new_role.role_id:
                role = member.guild.get_role(new_role.role_id)
                if role:
                    await member.add_roles(role, reason="Level change")
        except discord.HTTPException as e:
            logger.warning("Role sync failed for %s: %s", member.id, e)
