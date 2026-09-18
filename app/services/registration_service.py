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
        faceit_nickname: str | None = None,
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
            if faceit_nickname:
                fields["faceit_nickname"] = faceit_nickname
            updated = await self.players.update(existing.id, fields)
            logger.info("Player re-registered: %s/%s", guild_id, discord_user_id)
            return updated if updated else existing

        player = await self.players.create(
            guild_id, discord_user_id, among_us_name,
            nickname=nickname, faceit_nickname=faceit_nickname, default_elo=default_elo,
        )
        logger.info("Player registered: %s/%s (%s)", guild_id, discord_user_id, among_us_name)
        return player

    async def unregister(self, guild_id: int, discord_user_id: int) -> None:
        player = await self.players.get(guild_id, discord_user_id)
        if not player:
            return

        queue = (
            await self.client.table("queue_entries")
            .select("id")
            .eq("guild_id", guild_id)
            .eq("player_id", player.id)
            .eq("status", "WAITING")
            .execute()
        )
        if queue.data:
            raise ValueError("Та queue-д байна. Эхлээд queue-с гарна уу.")

        match_rows = (
            await self.client.table("match_players")
            .select("match_id")
            .eq("player_id", player.id)
            .execute()
        )
        match_ids = [r["match_id"] for r in (match_rows.data or [])]
        if match_ids:
            active = (
                await self.client.table("matches")
                .select("id")
                .in_("id", match_ids)
                .in_("status", ["CREATING", "READY", "IN_PROGRESS", "RESULT_PENDING"])
                .execute()
            )
            if active.data:
                raise ValueError("Та идэвхтэй match-д байна. Unregister хийх боломжгүй.")

        await self.players.delete(guild_id, discord_user_id)
        logger.info("Player unregistered: %s/%s", guild_id, discord_user_id)

    async def get(self, guild_id: int, discord_user_id: int) -> Player | None:
        return await self.players.get(guild_id, discord_user_id)
