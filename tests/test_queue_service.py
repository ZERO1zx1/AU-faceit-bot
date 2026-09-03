"""Integration tests for the queue service."""

import pytest

from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.services.queue_service import QueueService


async def _seed_players(session, guild_id, count=15):
    repo = PlayerRepository(session)
    ids = []
    for i in range(count):
        p = await repo.create(guild_id, 1000 + i, f"Player{i}", default_elo=1000)
        ids.append(p.id)
    await session.commit()
    return ids


async def _setup_guild(session, guild_id=100):
    repo = GuildRepository(session)
    await repo.upsert_settings(guild_id)
    await session.commit()


async def test_join_and_count(session):
    await _setup_guild(session)
    ids = await _seed_players(session, 100, count=5)
    svc = QueueService(session, queue_size=15)
    for pid in ids:
        await svc.join(100, pid)
    assert await svc.count(100) == 5


async def test_double_join_rejected(session):
    await _setup_guild(session)
    ids = await _seed_players(session, 100, count=1)
    svc = QueueService(session, queue_size=15)
    await svc.join(100, ids[0])
    with pytest.raises(ValueError):
        await svc.join(100, ids[0])


async def test_leave(session):
    await _setup_guild(session)
    ids = await _seed_players(session, 100, count=2)
    svc = QueueService(session, queue_size=15)
    await svc.join(100, ids[0])
    await svc.join(100, ids[1])
    await svc.leave(100, ids[0])
    assert await svc.count(100) == 1


async def test_is_full(session):
    await _setup_guild(session)
    ids = await _seed_players(session, 100, count=15)
    svc = QueueService(session, queue_size=15)
    for pid in ids:
        await svc.join(100, pid)
    assert await svc.is_full(100) is True


async def test_pop_all_clears(session):
    await _setup_guild(session)
    ids = await _seed_players(session, 100, count=15)
    svc = QueueService(session, queue_size=15)
    for pid in ids:
        await svc.join(100, pid)
    popped = await svc.pop_all(100)
    assert len(popped) == 15
    assert await svc.count(100) == 0
