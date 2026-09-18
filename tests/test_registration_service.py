"""Integration tests for the registration service."""

from __future__ import annotations

from typing import Any

import pytest

from app.repositories.guild_repository import GuildRepository
from app.services.registration_service import RegistrationService


async def _setup_guild(client: Any, guild_id: int = 100) -> None:
    repo = GuildRepository(client)
    await repo.upsert_settings(guild_id, default_elo=1000, win_elo=8, loss_elo=-6, queue_size=15)


async def test_register_success(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    player = await svc.register(100, 200, "Zero")
    assert player.among_us_name == "Zero"
    assert player.elo == 1000
    assert player.active is True


async def test_duplicate_register(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    await svc.register(100, 200, "Zero")
    with pytest.raises(ValueError):
        await svc.register(100, 200, "Zero")


async def test_duplicate_among_us_name(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    await svc.register(100, 200, "Zero")
    with pytest.raises(ValueError):
        await svc.register(100, 201, "Zero")


async def test_invalid_name(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    with pytest.raises(ValueError):
        await svc.register(100, 200, "Bad@Name!x")


async def test_register_persists_faceit_nickname(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    player = await svc.register(
        100, 200, "Zero", nickname="Z", faceit_nickname="zeRo_x"
    )
    assert player.faceit_nickname == "zeRo_x"
    persisted = await svc.get(100, 200)
    assert persisted is not None
    assert persisted.faceit_nickname == "zeRo_x"


async def test_reenroll_updates_faceit_nickname(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    player = await svc.register(100, 200, "Zero", faceit_nickname="old-name")
    await svc.unregister(100, 200)
    revived = await svc.register(100, 200, "Zero", faceit_nickname="new-name")
    assert revived.id == player.id
    assert revived.faceit_nickname == "new-name"


async def test_unregister_soft_deactivates(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    player = await svc.register(100, 200, "Zero")
    assert player.active is True

    await svc.unregister(100, 200)

    unregistered = await svc.get(100, 200)
    assert unregistered is not None
    assert unregistered.id == player.id
    assert unregistered.active is False
    assert unregistered.elo == 1000


async def test_unregister_rejects_queued_player(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    player = await svc.register(100, 200, "Zero")
    assert player.id is not None
    await svc.queue.add(100, player.id)
    with pytest.raises(ValueError):
        await svc.unregister(100, 200)
    active = await svc.get(100, 200)
    assert active is not None and active.active is True


async def test_unregister_rejects_player_in_active_match(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    player = await svc.register(100, 200, "Zero")
    assert player.id is not None
    await client.table("matches").insert(
        {
            "id": 1,
            "guild_id": 100,
            "status": "IN_PROGRESS",
            "display_id": "AU-0001",
        }
    ).execute()
    await client.table("match_players").insert(
        {"match_id": 1, "player_id": player.id}
    ).execute()
    with pytest.raises(ValueError):
        await svc.unregister(100, 200)


async def test_reenroll_reactivates_same_record(client: Any) -> None:
    await _setup_guild(client)
    svc = RegistrationService(client)
    player = await svc.register(100, 200, "Zero")
    await svc.unregister(100, 200)
    assert player.id is not None
    await svc.players.update(player.id, {"elo": 555})

    revived = await svc.register(100, 200, "Zero")

    assert revived.id == player.id
    assert revived.active is True
    assert revived.elo == 555
