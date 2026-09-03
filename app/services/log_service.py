"""Log service — audit log writing."""

import json

from app.models.audit import AuditLog
from supabase import AsyncClient


class LogService:
    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def log(
        self,
        guild_id: int,
        action_type: str,
        *,
        actor_id: int | None = None,
        target_entity: str | None = None,
        details: dict | None = None,
        success: bool = True,
        error_message: str | None = None,
    ) -> None:
        entry = AuditLog(
            guild_id=guild_id,
            action_type=action_type,
            actor_id=actor_id,
            target_entity=target_entity,
            details=json.dumps(details) if details else None,
            success=success,
            error_message=error_message,
        )
        await self.client.table("audit_logs").insert(entry.to_payload()).execute()
