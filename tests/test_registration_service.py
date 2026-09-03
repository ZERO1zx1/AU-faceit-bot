"""Integration tests for the registration service."""

import pytest

from app.repositories.guild_repository import GuildRepository
from app.services.registration_service import RegistrationService


async def _setup_guild(client, guild_id=100):
    repo = GuildRepository(client)
    await repo.upsert_settings(guild_id, default_elo=1000, win_elo=8, loss_elo=-6, queue_size=15)


async def test_register_success(client):
    await _setup_guild(client)
    svc = RegistrationService(client)
    player = await svc.register(100, 200, "Zero")
    assert player.among_us_name == "Zero"
    assert player.elo == 1000
    assert player.active is True


async def test_duplicate_register(client):
    await _setup_guild(client)
    svc = RegistrationService(client)
    await svc.register(100, 200, "Zero")
    with pytest.raises(ValueError):
        await svc.register(100, 200, "Zero")


async def test_duplicate_among_us_name(client):
    await _setup_guild(client)
    svc = RegistrationService(client)
    await svc.register(100, 200, "Zero")
    with pytest.raises(ValueError):
        await svc.register(100, 201, "Zero")


async def test_invalid_name(client):
    await _setup_guild(client)
    svc = RegistrationService(client)
    with pytest.raises(ValueError):
        await svc.register(100, 200, "Bad@Name!x")


async def test_unregister(client):
    await _setup_guild(client)
    svc = RegistrationService(client)
    await svc.register(100, 200, "Zero")
    await svc.unregister(100, 200)
    assert await svc.get(100, 200) is None
