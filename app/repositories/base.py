"""Base repository providing common Supabase REST table helpers."""

from __future__ import annotations

from typing import Any

from app.logging import get_logger
from app.models.base import SupabaseModel
from supabase import AsyncClient

logger = get_logger(__name__)


class BaseRepository[M: SupabaseModel]:
    """Thin wrapper around a single Supabase table.

    ``model`` must be a Pydantic model and ``table_name`` the associated
    PostgREST table name.
    """

    model: type[M]
    table_name: str

    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    # -- helpers ----------------------------------------------------------

    def _table(self):
        return self.client.table(self.table_name)

    @staticmethod
    def _rows(result: Any) -> list[dict]:
        return list(result.data or [])

    # -- CRUD -------------------------------------------------------------

    async def get_by_id(self, record_id: int) -> M | None:
        result = await self._table().select("*").eq("id", record_id).maybe_single().execute()
        return self.model.from_row(result.data) if result.data else None

    async def insert(self, obj: M, *, return_ids: bool = True) -> M | None:
        payload = obj.to_payload()
        result = await self._table().insert(payload).execute()
        rows = self._rows(result)
        if not rows:
            return None
        row = rows[0]
        if return_ids:
            # merge the server-assigned id/timestamps back onto the object
            merged = obj.model_copy(update=row)
            return merged
        return None

    async def update(self, record_id: int, fields: dict) -> None:
        result = await self._table().update(fields).eq("id", record_id).execute()
        return result

    async def delete_by_id(self, record_id: int) -> None:
        await self._table().delete().eq("id", record_id).execute()

    async def _select(self, *cols: str):
        """Return a select builder for the given columns (default ``*``)."""
        return self._table().select(*(cols or ("*",)))
