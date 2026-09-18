"""Audit log repository."""

from __future__ import annotations

from app.logging import get_logger
from app.models.audit import AuditLog
from app.repositories.base import BaseRepository
from supabase import AsyncClient

logger = get_logger(__name__)


class AuditLogRepository(BaseRepository[AuditLog]):
    model = AuditLog
    table_name = "audit_logs"

    def __init__(self, client: AsyncClient) -> None:
        super().__init__(client)
        self.client = client

    async def create(self, entry: AuditLog) -> AuditLog | None:
        return await self.insert(entry)
