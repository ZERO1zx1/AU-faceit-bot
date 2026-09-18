"""Shared pytest fixtures: in-memory fake Supabase client."""

from collections.abc import AsyncGenerator

import pytest_asyncio

from tests.fake_supabase import FakeSupabaseClient


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[FakeSupabaseClient, None]:
    yield FakeSupabaseClient()
