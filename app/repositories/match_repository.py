"""Match repository."""

from __future__ import annotations

from collections.abc import Sequence

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
        if result.data:
            return MatchPlayer.from_row(result.data[0])
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
        return Match.from_row(result.data) if result.data else None

    async def get_active(self, guild_id: int) -> Match | None:
        result = (
            await self._table()
            .select("*")
            .eq("guild_id", guild_id)
            .in_("status", ["CREATING", "READY", "IN_PROGRESS"])
            .maybe_single()
            .execute()
        )
        return Match.from_row(result.data) if result.data else None

    async def get_players(self, match_id: int) -> Sequence[MatchPlayer]:
        result = (
            await self.client.table("match_players")
            .select("*")
            .eq("match_id", match_id)
            .order("call_number")
            .execute()
        )
        return [MatchPlayer.from_row(row) for row in result.data or []]

    async def get_player_count(self, match_id: int) -> int:
        result = await (
            self.client.table("match_players").select("id").eq("match_id", match_id).execute()
        )
        return len(result.data or [])

    async def update_status(self, match_id: int, status: str) -> None:
        await self._table().update({"status": status}).eq("id", match_id).execute()

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
        rows = result.data or []
        seq = (rows[0]["id"] + 1) if rows and rows[0].get("id") else 1
        return f"AU-{seq:08d}"

    async def create_result(self, result: MatchResult) -> MatchResult:
        res = await self.client.table("match_results").insert(result.to_payload()).execute()
        if res.data:
            return MatchResult.from_row(res.data[0])
        return result

    async def create_submission(self, sub: ResultSubmission) -> ResultSubmission:
        res = (
            await self.client.table("result_submissions").insert(sub.to_payload()).execute()
        )
        if res.data:
            return ResultSubmission.from_row(res.data[0])
        return sub
