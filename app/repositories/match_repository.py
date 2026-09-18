"""Match repository."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from app.logging import get_logger
from app.models.match import Match, MatchPlayer, MatchResult, ResultSubmission
from app.repositories.base import BaseRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class MatchRepository(BaseRepository[Match]):
    model = Match
    table_name = "matches"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)
        self.client = client

    async def create(self, match: Match) -> Match:
        return (await self.insert(match)) or match

    async def add_player(self, player: MatchPlayer) -> MatchPlayer:
        result = await self.client.table("match_players").insert(player.to_payload()).execute()
        rows = self._rows(result)
        if rows:
            return MatchPlayer.from_row(rows[0])
        return player

    async def get(self, match_id: int) -> Match | None:
        return await super().get_by_id(match_id)

    async def get_by_display_id(self, display_id: str) -> Match | None:
        result = (
            await self._table()
            .select("*")
            .eq("display_id", display_id)
            .maybe_single()
            .execute()
        )
        row = self._single_row(result)
        return Match.from_row(row) if row is not None else None

    async def get_active(self, guild_id: int) -> Match | None:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .in_("status", ["CREATING", "READY", "IN_PROGRESS"])
            .maybe_single()
            .execute()
        )
        row = self._single_row(result)
        return Match.from_row(row) if row is not None else None

    async def list_active(self, guild_id: int | None = None) -> list[Match]:
        query = self._table().select("*").in_("status", ["CREATING", "READY", "IN_PROGRESS"])
        if guild_id is not None:
            query = query.eq("guild_id", guild_id)
        result = await query.execute()
        return [Match.from_row(row) for row in self._rows(result)]

    async def get_players(self, match_id: int) -> Sequence[MatchPlayer]:
        result = (
            await self.client.table("match_players")
            .select("*")
            .eq("match_id", match_id)
            .order("call_number")
            .execute()
        )
        return [MatchPlayer.from_row(row) for row in self._rows(result)]

    async def get_player_count(self, match_id: int) -> int:
        result = await (
            self.client.table("match_players").select("id").eq("match_id", match_id).execute()
        )
        return len(self._rows(result))

    async def has_active_match(
        self,
        guild_id: int,
        player_id: int,
        statuses: Sequence[str] = ("CREATING", "READY", "IN_PROGRESS", "RESULT_PENDING"),
    ) -> bool:
        """Return whether ``player_id`` sits in an active match in ``guild_id``."""
        match_rows = await (
            self.client.table("match_players")
            .select("match_id")
            .eq("player_id", player_id)
            .execute()
        )
        match_ids = [row["match_id"] for row in self._rows(match_rows)]
        if not match_ids:
            return False
        active = await (
            self.client.table("matches")
            .select("id")
            .eq("guild_id", guild_id)
            .in_("id", match_ids)
            .in_("status", list(statuses))
            .execute()
        )
        return bool(self._rows(active))

    async def update_status(self, match_id: int, status: str) -> None:
        await self._table().update({"status": status}).eq("id", match_id).execute()

    async def finalize_provisioning(self, match_id: int, text_id: int, voice_id: int) -> None:
        await (
            self._table()
            .update(
                {
                    "text_channel_id": text_id,
                    "voice_channel_id": voice_id,
                    "status": "IN_PROGRESS",
                    "started_at": datetime.now(UTC).isoformat(),
                }
            )
            .eq("id", match_id)
            .eq("status", "CREATING")
            .execute()
        )

    async def update_channels(self, match_id: int, text_id: int, voice_id: int) -> None:
        await (
            self._table()
            .update({"text_channel_id": text_id, "voice_channel_id": voice_id})
            .eq("id", match_id)
            .execute()
        )

    async def get_next_display_id(self, guild_id: int) -> str:
        result = (
            await self._table()
            .select("id")
            .eq("guild_id", guild_id)
            .order("id", desc=True)
            .limit(1)
            .execute()
        )
        rows = self._rows(result)
        seq = (rows[0]["id"] + 1) if rows and rows[0].get("id") else 1
        return f"AU-{seq:08d}"

    async def create_result(self, result: MatchResult) -> MatchResult:
        res = await self.client.table("match_results").insert(result.to_payload()).execute()
        rows = self._rows(res)
        if rows:
            return MatchResult.from_row(rows[0])
        return result

    async def create_submission(self, sub: ResultSubmission) -> ResultSubmission:
        res = (
            await self.client.table("result_submissions").insert(sub.to_payload()).execute()
        )
        rows = self._rows(res)
        if rows:
            return ResultSubmission.from_row(rows[0])
        return sub

    async def claim_from_queue(self, guild_id: int) -> dict[str, Any] | None:
        """Atomic queue claim + match creation, owned by Postgres."""
        result = await self.client.rpc(
            "claim_match_from_queue", {"p_guild_id": guild_id}
        ).execute()
        data = result.data
        if isinstance(data, list):
            return data[0] if data else None
        return data if isinstance(data, dict) else None

    async def create_match_from_ids(
        self, guild_id: int, player_ids_json: str
    ) -> dict[str, Any] | None:
        """Create a match from an explicit (shuffled) player id list via Postgres."""
        result = await self.client.rpc(
            "create_match",
            {"p_guild_id": guild_id, "p_player_ids": player_ids_json},
        ).execute()
        rows = self._rows(result)
        return rows[0] if rows else None
