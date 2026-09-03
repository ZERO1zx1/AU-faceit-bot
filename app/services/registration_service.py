"""Registration service."""

from __future__ import annotations

from app.logging import get_logger
from app.models.player import Player
from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.utils.validation import valid_among_us_name
from supabase import AsyncClient

logger = get_logger(__name__)


class RegistrationService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.players = PlayerRepository(client)
        self.guilds = GuildRepository(client)

    async def register(
        self,
        guild_id: int,
        discord_user_id: int,
        among_us_name: str,
        nickname: str | None = None,
    ) -> Player:
        settings = await self.guilds.get_settings(guild_id)
        default_elo = settings.default_elo if settings else 1000

        existing = await self.players.get(guild_id, discord_user_id)
        if existing and existing.active:
            raise ValueError("Already registered")

        dup_name = await self.players.get_by_among_us_name(guild_id, among_us_name)
        if dup_name:
            raise ValueError("Among Us name already taken")

        if not valid_among_us_name(among_us_name):
            raise ValueError("Invalid Among Us name")

        if existing and existing.id is not None:
            fields: dict = {"active": True, "among_us_name": among_us_name}
            if nickname:
                fields["nickname"] = nickname
            updated = await self.players.update(existing.id, fields)
            logger.info("Player re-registered: %s/%s", guild_id, discord_user_id)
            return updated if updated else existing

        player = await self.players.create(
            guild_id, discord_user_id, among_us_name, nickname=nickname, default_elo=default_elo
        )
        logger.info("Player registered: %s/%s (%s)", guild_id, discord_user_id, among_us_name)
        return player

    async def unregister(self, guild_id: int, discord_user_id: int) -> None:
        await self.players.delete(guild_id, discord_user_id)
        logger.info("Player unregistered: %s/%s", guild_id, discord_user_id)

    async def get(self, guild_id: int, discord_user_id: int) -> Player | None:
        return await self.players.get(guild_id, discord_user_id)
