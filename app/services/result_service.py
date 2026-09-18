"""Result service."""

from __future__ import annotations

import json
from collections.abc import Sequence

from app.logging import get_logger
from app.models.match import Match, MatchPlayer, ResultSubmission
from app.models.player import Player
from app.repositories.guild_repository import GuildRepository
from app.repositories.match_repository import MatchRepository
from app.repositories.player_repository import PlayerRepository
from app.repositories.result_repository import ResultRepository
from app.utils.constants import (
    MATCH_STATUS_IN_PROGRESS,
    MATCH_STATUS_READY,
    SIDES_CREWMATE,
    SIDES_IMPOSTOR,
)
from supabase import AsyncClient

logger = get_logger(__name__)


class ResultService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.match_repo = MatchRepository(client)
        self.players = PlayerRepository(client)
        self.guilds = GuildRepository(client)
        self.submissions = ResultRepository(client)

    async def get_match(self, match_id: int) -> Match | None:
        return await self.match_repo.get(match_id)

    async def get_match_players(self, match_id: int) -> Sequence[MatchPlayer]:
        return await self.match_repo.get_players(match_id)

    async def get_player(self, guild_id: int, discord_user_id: int) -> Player | None:
        return await self.players.get(guild_id, discord_user_id)

    async def get_player_by_id(self, player_id: int) -> Player | None:
        return await self.players.get_by_id(player_id)

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

        Validates the submitter/impostors against the match and delegates the
        insert + match status flip to the ``submit_match_result`` Postgres
        function so the whole operation is atomic and one pending submission
        per match is guaranteed by a partial unique index.
        """
        if winner_side not in (SIDES_CREWMATE, SIDES_IMPOSTOR):
            raise ValueError("Winner-ийн сонголт буруу байна.")
        if not screenshot_url or not screenshot_url.strip():
            raise ValueError("Result-ийн screenshot заавал оруулна уу.")

        match = await self.match_repo.get(match_id)
        if match is None or match.guild_id != guild_id:
            raise ValueError("Энэ серверт тохирох match олдсонгүй.")
        if match.result_processed or match.status not in (
            MATCH_STATUS_READY,
            MATCH_STATUS_IN_PROGRESS,
        ):
            raise ValueError("Энэ match-ийн result илгээх боломжгүй байна.")

        match_players = await self.match_repo.get_players(match_id)
        allowed_player_ids = {player.player_id for player in match_players}

        submitter = await self.players.get(guild_id, submitted_by)
        if not submitter or submitter.id not in allowed_player_ids:
            raise ValueError("Зөвхөн энэ match-д оролцсон тоглогч result илгээнэ.")

        unique_impostors = list(dict.fromkeys(impostor_player_ids))
        if len(unique_impostors) != len(impostor_player_ids):
            raise ValueError("Impostor тоглогч давхар сонгогдсон байна.")
        if not 1 <= len(unique_impostors) <= 3:
            raise ValueError("Impostor тоглогчийн тоо 1–3 байх ёстой.")
        for impostor_id in unique_impostors:
            if impostor_id not in allowed_player_ids:
                raise ValueError("Бүх impostor тоглогч энэ match-ийн тоглогч байх ёстой.")

        params = {
            "p_guild_id": guild_id,
            "p_match_id": match_id,
            "p_submitted_by": submitted_by,
            "p_winner_side": winner_side,
            "p_impostor_player_ids": json.dumps(unique_impostors),
            "p_screenshot_url": screenshot_url,
        }
        row = await self.submissions.submit(params)
        if row is not None:
            logger.info(
                "Result submitted: match=%s by=%s winner=%s",
                match_id,
                submitted_by,
                winner_side,
            )
            return ResultSubmission.from_row(row)
        raise RuntimeError("submit_match_result RPC returned no submission")

    async def approve_result(
        self,
        match_id: int,
        *,
        approved_by: int,
        guild_id: int | None = None,
        win_elo: int | None = None,
        loss_elo: int | None = None,
    ) -> Match:
        """Approve a pending result and settle Elo atomically.

        Guild-level ``win_elo`` / ``loss_elo`` settings are used when explicit
        values are not provided. The ``approve_match_result`` Postgres function
        covers the pending-submission lookup, Elo settle, player statistics and
        match finalization in a single transaction.
        """
        match = await self.match_repo.get(match_id)
        if match is None:
            raise ValueError("Match олдсонгүй.")
        if guild_id is not None and match.guild_id != guild_id:
            raise ValueError("Энэ серверт тохирох match олдсонгүй.")

        settings = await self.guilds.get_settings(match.guild_id)
        win = win_elo if win_elo is not None else (settings.win_elo if settings else 8)
        loss = loss_elo if loss_elo is not None else (settings.loss_elo if settings else -6)

        params: dict[str, object] = {
            "p_match_id": match_id,
            "p_approved_by": approved_by,
            "p_win_elo": win,
            "p_loss_elo": loss,
        }
        await self.submissions.approve(params)
        logger.info(
            "Result approved: match=%s by=%s win=%d loss=%d",
            match_id,
            approved_by,
            win,
            loss,
        )
        return match

    async def reject_result(
        self,
        match_id: int,
        *,
        rejected_by: int,
        guild_id: int | None = None,
        reason: str | None = None,
    ) -> Match:
        """Atomically reject the pending submission and reopen the match.

        The moderator and (optional) reason are persisted on the submission so
        the rejection is auditable and cannot be accidentally approved later.
        """
        match = await self.match_repo.get(match_id)
        if match is None:
            raise ValueError("Match олдсонгүй.")
        if guild_id is not None and match.guild_id != guild_id:
            raise ValueError("Энэ серверт тохирох match олдсонгүй.")
        await self.submissions.reject(
            {
                "p_match_id": match_id,
                "p_rejected_by": rejected_by,
                "p_reason": reason,
            }
        )
        logger.info("Result rejected: match=%s by=%s reason=%r", match_id, rejected_by, reason)
        return match

    async def set_approval_message(self, submission_id: int, message_id: int) -> None:
        await self.submissions.set_approval_message(submission_id, message_id)

    async def get_pending_submissions(self) -> list[ResultSubmission]:
        return await self.submissions.list_pending()
