"""Shared pytest fixtures: in-memory fake Supabase client."""

import pytest_asyncio

from tests.fake_supabase import FakeSupabaseClient


@pytest_asyncio.fixture
async def client():
    yield FakeSupabaseClient()
