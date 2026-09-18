"""Integration tests for the queue service."""

import pytest

from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.services.match_service import MatchService
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


async def test_join_rejects_player_from_another_guild(client):
    await _setup_guild(client, guild_id=100)
    await _setup_guild(client, guild_id=200)
    player_id = (await _seed_players(client, 200, count=1))[0]

    with pytest.raises(ValueError, match="бүртгүүлэх"):
        await QueueService(client).join(100, player_id)

    assert await QueueService(client).count(100) == 0


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


async def test_status_returns_count_and_average_elo(client):
    await _setup_guild(client)
    repo = PlayerRepository(client)
    first = await repo.create(100, 3001, "AverageOne", default_elo=900)
    second = await repo.create(100, 3002, "AverageTwo", default_elo=1100)
    queue = QueueService(client)
    await queue.join(100, first.id)
    await queue.join(100, second.id)

    assert await queue.get_status(100) == (2, 1000)


async def test_pop_all_clears(client):
    await _setup_guild(client)
    ids = await _seed_players(client, 100, count=15)
    svc = QueueService(client, queue_size=15)
    for pid in ids:
        await svc.join(100, pid)
    popped = await svc.pop_all(100)
    assert len(popped) == 15
    assert await svc.count(100) == 0


async def test_claim_match_requires_full_queue_without_removing_players(client):
    await _setup_guild(client)
    ids = await _seed_players(client, 100, count=14)
    queue = QueueService(client, queue_size=15)
    for player_id in ids:
        await queue.join(100, player_id)

    claimed = await MatchService(client).claim_from_queue(100)

    assert claimed is None
    assert await queue.count(100) == 14


async def test_claim_match_removes_only_configured_queue_size(client):
    await _setup_guild(client)
    ids = await _seed_players(client, 100, count=17)
    queue = QueueService(client, queue_size=15)
    for player_id in ids:
        await queue.join(100, player_id)

    claimed = await MatchService(client).claim_from_queue(100)

    assert claimed is not None
    match, selected = claimed
    assert match.guild_id == 100
    assert selected == ids[:15]
    assert await queue.count(100) == 2
    assert len(await MatchService(client).get_players(match.id)) == 15


async def test_claim_match_uses_guild_queue_size(client):
    repo = GuildRepository(client)
    await repo.upsert_settings(100, queue_size=2)
    ids = await _seed_players(client, 100, count=3)
    queue = QueueService(client, queue_size=2)
    for player_id in ids:
        await queue.join(100, player_id)

    claimed = await MatchService(client).claim_from_queue(100)

    assert claimed is not None
    _match, selected = claimed
    assert selected == ids[:2]
    assert await queue.count(100) == 1
