"""Supabase async client singleton.

Provides a shared ``AsyncClient`` for the whole application. The client is
created lazily via ``await init_client()`` (called once at startup) so that
importing the module does not require valid credentials at import time.
"""

from __future__ import annotations

from app.config import settings
from app.logging import get_logger
from supabase import AsyncClient, create_async_client

logger = get_logger(__name__)

_client: AsyncClient | None = None


async def init_client() -> None:
    """Create the application-wide Supabase async client (call once at startup)."""
    global _client
    if _client is not None:
        return
    url = settings.supabase_url
    key = settings.supabase_key
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_KEY must be set in the environment/.env "
            "to use the Supabase REST API."
        )
    logger.info("Creating Supabase client for %s", url.split(".") [0])
    _client = await create_async_client(url, key)


def get_client() -> AsyncClient:
    """Return the application-wide Supabase async client."""
    if _client is None:
        raise RuntimeError(
            "Supabase client not initialized — call await init_client() first."
        )
    return _client


async def dispose_client() -> None:
    """Close the underlying connection pools for a graceful shutdown."""
    global _client
    if _client is None:
        return
    try:
        await _client.aclose()
    except Exception as exc:  # pragma: no cover - best effort on shutdown
        logger.warning("Error closing Supabase client: %s", exc)
    finally:
        _client = None
