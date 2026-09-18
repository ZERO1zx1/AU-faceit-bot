"""Administrative player operations shared by prefix and slash commands."""

from __future__ import annotations

from typing import Any

from app.models.ban import Ban
from app.models.elo import EloTransaction
from app.repositories.ban_repository import BanRepository
from app.repositories.elo_repository import EloRepository
from app.repositories.player_repository import PlayerRepository
from app.services.log_service import LogService
from supabase import AsyncClient


class AdminService:
    def __init__(self, client: AsyncClient, bot: Any | None = None) -> None:
        self.client = client
        self.players = PlayerRepository(client)
        self.elo_repo = EloRepository(client)
        self.bans = BanRepository(client)
        self.logs = LogService(client, bot)

    async def adjust_elo(
        self,
        guild_id: int,
        discord_user_id: int,
        amount: int,
        *,
        actor_id: int,
        target_name: str,
    ) -> tuple[int, int]:
        player = await self.players.get(guild_id, discord_user_id)
        if not player or player.id is None:
            raise ValueError("Player not found")

        old_elo = player.elo
        new_elo = old_elo + amount
        await self.players.update(
            player.id, {"elo": new_elo, "peak_elo": max(player.peak_elo, new_elo)}
        )
        await self.elo_repo.create_transaction(
            EloTransaction(
                guild_id=guild_id,
                player_id=player.id,
                old_elo=old_elo,
                change=amount,
                new_elo=new_elo,
                reason="Manual adjustment",
                transaction_type="MANUAL",
                created_by=actor_id,
            )
        )
        await self.logs.log(
            guild_id,
            "ELO_MANUAL",
            actor_id=actor_id,
            target_entity=target_name,
            details={"old": old_elo, "new": new_elo, "delta": amount},
        )
        return old_elo, new_elo

    async def ban_player(
        self,
        guild_id: int,
        discord_user_id: int,
        *,
        reason: str,
        actor_id: int,
        target_name: str,
    ) -> None:
        player = await self.players.get(guild_id, discord_user_id)
        if not player or player.id is None:
            raise ValueError("Player not found")

        await self.players.update(player.id, {"banned": True})
        ban = Ban(
            guild_id=guild_id,
            player_id=player.id,
            reason=reason,
            banned_by=actor_id,
        )
        await self.bans.create(ban)
        await self.logs.log(
            guild_id,
            "BAN",
            actor_id=actor_id,
            target_entity=target_name,
            details={"reason": reason},
        )

    async def unban_player(
        self,
        guild_id: int,
        discord_user_id: int,
        *,
        actor_id: int,
        target_name: str,
    ) -> None:
        player = await self.players.get(guild_id, discord_user_id)
        if not player or player.id is None:
            raise ValueError("Player not found")

        await self.players.update(player.id, {"banned": False})
        await self.bans.deactivate_active(guild_id, player.id)
        await self.logs.log(
            guild_id,
            "UNBAN",
            actor_id=actor_id,
            target_entity=target_name,
        )
