"""Supabase async client singleton.

Provides a shared ``AsyncClient`` for the whole application. The client is
created lazily on first use so that importing the module does not require
valid credentials at import time.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.logging import get_logger
from supabase import AsyncClient, create_async_client

logger = get_logger(__name__)


@lru_cache
def _client_kwargs() -> dict:
    url = settings.supabase_url
    key = settings.supabase_key
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the environment/.env "
            "to use the Supabase REST API."
        )
    return {"supabase_url": url, "supabase_key": key, "postgrest_client_timeout": 30}


@lru_cache
def get_client() -> AsyncClient:
    """Return the application-wide Supabase async client."""
    kwargs = _client_kwargs()
    logger.info("Creating Supabase client for %s", kwargs["supabase_url"].split(".")[0])
    return create_async_client(**kwargs)


async def dispose_client() -> None:
    """Close the underlying connection pools for a graceful shutdown."""
    client = get_client()
    try:
        await client.aclose()
    except Exception as exc:  # pragma: no cover - best effort on shutdown
        logger.warning("Error closing Supabase client: %s", exc)
