"""Integration tests for elo and match services."""

from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.services.elo_service import EloService
from app.services.match_service import MatchService
from app.utils.constants import SIDES_CREWMATE, SIDES_IMPOSTOR


async def _setup(session, guild_id=100, count=15):
    repo = GuildRepository(session)
    await repo.upsert_settings(guild_id)
    await session.commit()
    preg = PlayerRepository(session)
    ids = []
    for i in range(count):
        p = await preg.create(guild_id, 2000 + i, f"P{i}", default_elo=1000 + i)
        ids.append(p.id)
    await session.commit()
    return ids


async def test_create_match_assigns_unique_calls(session):
    ids = await _setup(session)
    svc = MatchService(session)
    match = await svc.create_match(100, ids)
    players = await svc.get_players(match.id)
    assert len(players) == 15
    calls = [p.call_number for p in players]
    assert sorted(calls) == list(range(1, 16))
    assert match.average_elo == sum(1000 + i for i in range(15)) // 15


async def test_apply_elo_crewmate_win(session):
    ids = await _setup(session)
    svc = EloService(session)
    player_dicts = [
        {"player_id": pid, "elo_before": 1000 + i, "role_side": SIDES_CREWMATE}
        for i, pid in enumerate(ids)
    ]
    await svc.apply_match_result(
        100, player_dicts, winner_side=SIDES_CREWMATE, win_delta=8, loss_delta=-6
    )
    preg = PlayerRepository(session)
    first = await preg.get_by_id(ids[0])
    assert first.elo == 1000 + 8


async def test_apply_elo_impostor_win(session):
    ids = await _setup(session)
    svc = EloService(session)
    player_dicts = [
        {"player_id": pid, "elo_before": 1000 + i, "role_side": SIDES_IMPOSTOR}
        for i, pid in enumerate(ids)
    ]
    await svc.apply_match_result(
        100, player_dicts, winner_side=SIDES_IMPOSTOR, win_delta=8, loss_delta=-6
    )
    preg = PlayerRepository(session)
    first = await preg.get_by_id(ids[0])
    assert first.elo == 1000 + 8
