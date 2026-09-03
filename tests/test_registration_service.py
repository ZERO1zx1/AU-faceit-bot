"""Integration tests for the registration service."""

import pytest

from app.repositories.guild_repository import GuildRepository
from app.services.registration_service import RegistrationService


async def _setup_guild(session, guild_id=100):
    repo = GuildRepository(session)
    await repo.upsert_settings(guild_id, default_elo=1000, win_elo=8, loss_elo=-6, queue_size=15)
    await session.commit()


async def test_register_success(session):
    await _setup_guild(session)
    svc = RegistrationService(session)
    player = await svc.register(100, 200, "Zero")
    assert player.among_us_name == "Zero"
    assert player.elo == 1000
    assert player.active is True


async def test_duplicate_register(session):
    await _setup_guild(session)
    svc = RegistrationService(session)
    await svc.register(100, 200, "Zero")
    with pytest.raises(ValueError):
        await svc.register(100, 200, "Zero")


async def test_duplicate_among_us_name(session):
    await _setup_guild(session)
    svc = RegistrationService(session)
    await svc.register(100, 200, "Zero")
    with pytest.raises(ValueError):
        await svc.register(100, 201, "Zero")


async def test_invalid_name(session):
    await _setup_guild(session)
    svc = RegistrationService(session)
    with pytest.raises(ValueError):
        await svc.register(100, 200, "Bad@Name!x")


async def test_unregister(session):
    await _setup_guild(session)
    svc = RegistrationService(session)
    await svc.register(100, 200, "Zero")
    await svc.unregister(100, 200)
    assert await svc.get(100, 200) is None
