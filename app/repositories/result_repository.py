"""Result submission repository."""

from __future__ import annotations

from typing import Any

from app.models.match import ResultSubmission
from app.repositories.base import BaseRepository
from supabase import AsyncClient


class ResultRepository(BaseRepository[ResultSubmission]):
    model = ResultSubmission
    table_name = "result_submissions"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)

    async def list_pending(self) -> list[ResultSubmission]:
        result = await self._table().select("*").eq("status", "PENDING").execute()
        return [ResultSubmission.from_row(row) for row in self._rows(result)]

    async def set_approval_message(self, submission_id: int, message_id: int) -> None:
        await (
            self._table()
            .update({"approval_message_id": message_id})
            .eq("id", submission_id)
            .execute()
        )

    @staticmethod
    def _params(**kwargs: object) -> dict[str, object]:
        return kwargs

    async def submit(self, params: dict[str, object]) -> dict[str, Any] | None:
        result = await self.client.rpc("submit_match_result", params).execute()
        rows = self._rows(result)
        return rows[0] if rows else None

    async def approve(self, params: dict[str, object]) -> None:
        await self.client.rpc("approve_match_result", params).execute()

    async def reject(self, params: dict[str, object]) -> None:
        await self.client.rpc("reject_match_result", params).execute()
