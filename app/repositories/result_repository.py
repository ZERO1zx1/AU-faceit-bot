"""Result submission repository."""

from __future__ import annotations

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
        return [ResultSubmission.from_row(row) for row in (result.data or [])]

    async def set_approval_message(self, submission_id: int, message_id: int) -> None:
        await (
            self._table()
            .update({"approval_message_id": message_id})
            .eq("id", submission_id)
            .execute()
        )
