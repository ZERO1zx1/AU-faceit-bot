"""Result service."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.match import ResultSubmission
from app.repositories.match_repository import MatchRepository
from app.services.elo_service import EloService
from app.utils.constants import (
    MATCH_STATUS_COMPLETED,
    MATCH_STATUS_RESULT_PENDING,
    SIDES_CREWMATE,
    SIDES_IMPOSTOR,
)

logger = get_logger(__name__)


class ResultService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.match_repo = MatchRepository(session)
        self.elo_svc = EloService(session)

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
        match = await self.match_repo.get(match_id)
        if not match:
            raise ValueError("Match not found")
        if match.result_processed:
            raise ValueError("Result already processed")
        if match.status not in (MATCH_STATUS_RESULT_PENDING, "IN_PROGRESS"):
            raise ValueError("Invalid match status")

        sub = ResultSubmission(
            match_id=match_id,
            guild_id=guild_id,
            submitted_by=submitted_by,
            winner_side=winner_side,
            impostor_player_ids=",".join(str(i) for i in impostor_player_ids),
            screenshot_url=screenshot_url,
            status="PENDING",
        )
        self.session.add(sub)
        await self.session.flush()
        match.status = MATCH_STATUS_RESULT_PENDING
        match.result_submitted_by = submitted_by
        await self.session.commit()
        logger.info("Result submitted: match=%s by=%s", match.display_id, submitted_by)
        return sub

    async def approve_result(
        self,
        match_id: int,
        *,
        approved_by: int,
        win_elo: int = 8,
        loss_elo: int = -6,
    ) -> None:
        match = await self.match_repo.get(match_id)
        if not match:
            raise ValueError("Match not found")
        if match.result_processed:
            raise ValueError("Result already processed")

        subs = await self.session.execute(
            self.session.query(ResultSubmission).filter(
                ResultSubmission.match_id == match_id, ResultSubmission.status == "PENDING"
            )
        )
        sub = subs.scalars().first()
        if not sub:
            raise ValueError("No pending result submission")

        players = await self.match_repo.get_players(match_id)
        impostor_ids = set(int(x) for x in sub.impostor_player_ids.split(",") if x)
        player_dicts = []
        for mp in players:
            role_side = SIDES_IMPOSTOR if mp.player_id in impostor_ids else SIDES_CREWMATE
            mp.role_side = role_side
            player_dicts.append(
                {"player_id": mp.player_id, "elo_before": mp.elo_before, "role_side": role_side}
            )

        await self.elo_svc.apply_match_result(
            match.guild_id,
            player_dicts,
            winner_side=sub.winner_side,
            win_delta=win_elo,
            loss_delta=loss_elo,
            match_id=match_id,
            approved_by=approved_by,
        )

        sub.status = "APPROVED"
        sub.approved_by = approved_by
        sub.approved_at = datetime.utcnow()
        match.result_processed = True
        match.result_approved_by = approved_by
        match.status = MATCH_STATUS_COMPLETED
        match.finished_at = datetime.utcnow()
        await self.session.commit()
        logger.info("Result approved: match=%s by=%s", match.display_id, approved_by)
