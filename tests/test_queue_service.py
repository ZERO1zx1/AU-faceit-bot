"""Integration tests for the queue service."""

import pytest

from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.services.queue_service import QueueService


async def _seed_players(client, guild_id, count=15):
    repo = PlayerRepository(client)
    ids = []
    for i in range(count):
        p = await repo.create(guild_id, 1000 + i, f"Player{i}", default_elo=1000)
        ids.append(p.id)
    return ids


async def _setup_guild(client, guild_id=100):
    repo = GuildRepository(client)
    await repo.upsert_settings(guild_id)


async def test_join_and_count(client):
    await _setup_guild(client)
    ids = await _seed_players(client, 100, count=5)
    svc = QueueService(client, queue_size=15)
    for pid in ids:
        await svc.join(100, pid)
    assert await svc.count(100) == 5


async def test_double_join_rejected(client):
    await _setup_guild(client)
    ids = await _seed_players(client, 100, count=1)
    svc = QueueService(client, queue_size=15)
    await svc.join(100, ids[0])
    with pytest.raises(ValueError):
        await svc.join(100, ids[0])


async def test_leave(client):
    await _setup_guild(client)
    ids = await _seed_players(client, 100, count=2)
    svc = QueueService(client, queue_size=15)
    await svc.join(100, ids[0])
    await svc.join(100, ids[1])
    await svc.leave(100, ids[0])
    assert await svc.count(100) == 1


async def test_is_full(client):
    await _setup_guild(client)
    ids = await _seed_players(client, 100, count=15)
    svc = QueueService(client, queue_size=15)
    for pid in ids:
        await svc.join(100, pid)
    assert await svc.is_full(100) is True


async def test_pop_all_clears(client):
    await _setup_guild(client)
    ids = await _seed_players(client, 100, count=15)
    svc = QueueService(client, queue_size=15)
    for pid in ids:
        await svc.join(100, pid)
    popped = await svc.pop_all(100)
    assert len(popped) == 15
    assert await svc.count(100) == 0
