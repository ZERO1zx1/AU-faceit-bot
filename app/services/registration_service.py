"""Registration service."""

from __future__ import annotations

from app.logging import get_logger
from app.models.player import Player
from app.repositories.guild_repository import GuildRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.player_repository import PlayerRepository
from app.repositories.queue_repository import QueueRepository
from app.utils.constants import (
    MATCH_STATUS_CREATING,
    MATCH_STATUS_IN_PROGRESS,
    MATCH_STATUS_READY,
    MATCH_STATUS_RESULT_PENDING,
)
from app.utils.validation import valid_among_us_name
from supabase import AsyncClient

logger = get_logger(__name__)

_ACTIVE_MATCH_STATUSES_FOR_UNREGISTER = (
    MATCH_STATUS_CREATING,
    MATCH_STATUS_READY,
    MATCH_STATUS_IN_PROGRESS,
    MATCH_STATUS_RESULT_PENDING,
)

# Decision: an inactive player's Among Us name stays reserved for the guild
# (the DB unique constraint on (guild_id, among_us_name) applies regardless of
# ``active``). Another user cannot claim it; the original owner can reuse it on
# re-registration because the duplicate check skips their own record.


class RegistrationService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.players = PlayerRepository(client)
        self.guilds = GuildRepository(client)
        self.queue = QueueRepository(client)
        self.matches = MatchRepository(client)

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
        if dup_name and (existing is None or dup_name.id != existing.id):
            raise ValueError("Among Us name already taken")

        if not valid_among_us_name(among_us_name):
            raise ValueError("Invalid Among Us name")

        if existing and existing.id is not None:
            fields: dict[str, object] = {"active": True, "among_us_name": among_us_name}
            if nickname:
                fields["nickname"] = nickname
            if faceit_nickname:
                fields["faceit_nickname"] = faceit_nickname
            updated = await self.players.update(existing.id, fields)
            logger.info("Player re-registered (reactivated): %s/%s", guild_id, discord_user_id)
            return updated if updated else existing

        player = await self.players.create(
            guild_id, discord_user_id, among_us_name,
            nickname=nickname, faceit_nickname=faceit_nickname, default_elo=default_elo,
        )
        logger.info("Player registered: %s/%s (%s)", guild_id, discord_user_id, among_us_name)
        return player

    async def unregister(self, guild_id: int, discord_user_id: int) -> None:
        """Remove a player from the ladder without destroying history.

        This is a guarded soft deactivation:
        - Rejected while the player has a WAITING queue entry or sits in any
          CREATING/READY/IN_PROGRESS/RESULT_PENDING match.
        - Otherwise sets ``active = false`` on the player row. The row, its
          match_players participation, matches, Elo transactions and voice
          history all remain intact and re-registration reactivates the row.
        """
        player = await self.players.get(guild_id, discord_user_id)
        if not player or player.id is None:
            return

        if await self.queue.get_entry(guild_id, player.id):
            raise ValueError("Та queue-д байна. Эхлээд queue-с гарна уу.")

        if await self.matches.has_active_match(
            guild_id, player.id, statuses=_ACTIVE_MATCH_STATUSES_FOR_UNREGISTER
        ):
            raise ValueError("Та идэвхтэй match-д байна. Unregister хийх боломжгүй.")

        await self.players.deactivate(player.id)
        logger.info("Player unregistered (soft): %s/%s", guild_id, discord_user_id)

    async def get(self, guild_id: int, discord_user_id: int) -> Player | None:
        return await self.players.get(guild_id, discord_user_id)
