"""Result service."""

from __future__ import annotations

import json

from app.logging import get_logger
from app.models.match import ResultSubmission
from app.repositories.match_repository import MatchRepository
from app.services.elo_service import EloService
from supabase import AsyncClient

logger = get_logger(__name__)


class ResultService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.match_repo = MatchRepository(client)
        self.elo_svc = EloService(client)

    async def submit_result(
        self,
        guild_id: int,
        match_id: int,
        *,
        submitted_by: int,
        winner_side: str,
        impostor_player_ids: list[int],
        screenshot_url: str | None = None,
    ) -> ResultSubmission:
        """Submit a result for approval.

        Delegates to the ``submit_match_result`` Postgres function so the new
        submission row and the match status update happen atomically.
        """
        params = {
            "p_guild_id": guild_id,
            "p_match_id": match_id,
            "p_submitted_by": submitted_by,
            "p_winner_side": winner_side,
            "p_impostor_player_ids": json.dumps(impostor_player_ids),
            "p_screenshot_url": screenshot_url,
        }
        res = await self.client.rpc("submit_match_result", params).execute()
        rows = res.data if res.data else None
        if isinstance(rows, list) and rows:
            return ResultSubmission.from_row(rows[0])
        # fallback: return a local submission shape (no server row available)
        return ResultSubmission(
            match_id=match_id,
            guild_id=guild_id,
            submitted_by=submitted_by,
            winner_side=winner_side,
            impostor_player_ids=",".join(str(i) for i in impostor_player_ids),
            screenshot_url=screenshot_url,
            status="PENDING",
        )

    async def approve_result(
        self,
        match_id: int,
        *,
        approved_by: int,
        win_elo: int = 8,
        loss_elo: int = -6,
    ) -> None:
        """Approve a pending result and settle Elo atomically.

        Delegates to the ``approve_match_result`` Postgres function covering the
        pending-submission lookup, role assignment, Elo settlement and match
        finalization in a single transaction.
        """
        params = {
            "p_match_id": match_id,
            "p_approved_by": approved_by,
            "p_win_elo": win_elo,
            "p_loss_elo": loss_elo,
        }
        await self.client.rpc("approve_match_result", params).execute()
        logger.info("Result approved: match=%s by=%s", match_id, approved_by)
