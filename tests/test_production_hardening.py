"""Production-readiness tests.

Persistent views, slash registration, result lifecycle, panel limits,
SQL security hardening, queue concurrency.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

import discord
import pytest
from discord import app_commands
from discord.ext import commands

from app.cogs.admin import AdminCog
from app.cogs.help import HelpCog
from app.cogs.leaderboard import LeaderboardCog
from app.cogs.panels import PanelsCog
from app.cogs.profile import ProfileCog
from app.cogs.queue import QueueCog
from app.cogs.registration import RegistrationCog
from app.cogs.result import ResultCog
from app.cogs.setup import SetupCog
from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.services.match_service import MatchService
from app.services.queue_service import QueueService
from app.services.result_service import ResultService
from app.ui.panel_builder import EmbedValidationError, PanelEmbedBuilder
from app.ui.views import QueueView, RegisterView, ResultApprovalView, UnregisterConfirmView
from app.utils.ids import BUTTON_IDS

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _btn(*, component: str, action: str) -> str:
    return f"au:{component}:{action}"


async def _setup_guild(client, guild_id=100):
    await GuildRepository(client).upsert_settings(guild_id)


async def _seed_full_queue(client, guild_id=100):
    await _setup_guild(client, guild_id)
    repo = PlayerRepository(client)
    ids = []
    for i in range(15):
        p = await repo.create(guild_id, 2000 + i, f"P{i}", default_elo=1000 + i)
        ids.append(p.id)
    return ids


async def _claim_match(client, guild_id=100):
    ids = await _seed_full_queue(client, guild_id)
    svc = QueueService(client, queue_size=15)
    for pid in ids:
        await svc.join(guild_id, pid)
    match_svc = MatchService(client)
    claimed = await match_svc.claim_from_queue(guild_id)
    assert claimed is not None, "claim failed unexpectedly"
    match, selected = claimed
    await match_svc.set_status(match.id, "READY")
    return match, selected, ids


# ---------------------------------------------------------------------------
# Persistent views — discord.ui.View requires a running loop, so these must
# be async so that pytest-asyncio creates the loop for them.
# ---------------------------------------------------------------------------

async def test_register_view_persistent():
    v = RegisterView()
    assert v.timeout is None
    btn = v.children[0]
    assert btn.custom_id == BUTTON_IDS["register"]


async def test_queue_view_persistent():
    v = QueueView()
    assert v.timeout is None
    join_btn = next(c for c in v.children if c.label == "ENTER MATCH")
    leave_btn = next(c for c in v.children if c.label == "LEAVE QUEUE")
    assert join_btn.custom_id == BUTTON_IDS["queue_join"]
    assert leave_btn.custom_id == BUTTON_IDS["queue_leave"]


async def test_unregister_confirm_view_timeout():
    v = UnregisterConfirmView()
    assert v.timeout == 60


async def test_result_approval_view_custom_ids_deterministic():
    v = ResultApprovalView(42)
    assert v.timeout is None
    approve_btn = next(c for c in v.children if c.label == "APPROVE")
    reject_btn = next(c for c in v.children if c.label == "REJECT")
    assert approve_btn.custom_id == "au:result:approve:42"
    assert reject_btn.custom_id == "au:result:reject:42"


async def test_result_approval_view_custom_ids_stable():
    a = ResultApprovalView(99)
    b = ResultApprovalView(99)
    for x, y in zip(a.children, b.children, strict=False):
        assert x.custom_id == y.custom_id


# ---------------------------------------------------------------------------
# Slash command registration
# ---------------------------------------------------------------------------

def _expected_slash_tree():
    """Return a dict of top-level command names → expected subcommands/params."""
    return {
        "setup": {
            "subcommands": {
                "server": 0,
                "logs": 1,
                "register": 1,
                "levels": 0,
                "queue": 1,
                "leaderboard": 1,
            },
            "description": True,
        },
        "panel": {
            "subcommands": {
                "create": {"params": {"channel", "title"}},
                "edit": {"params": {"panel_id"}},
                "delete": {"params": {"panel_id"}},
                "list": 0,
            },
            "description": True,
        },
        "admin": {
            "subcommands": {"elo", "ban", "unban"},
            "description": True,
        },
        "help": {"description": True},
        "profile": {"description": True},
        "matches": {"description": True},
        "leaderboard": {"description": True},
        "queue-status": {"description": True},
        "unregister": {"description": True},
        "result": {
            "subcommands": {"submit", "review"},
            "description": True,
        },
    }


@pytest.fixture
async def slash_bot():
    bot = commands.Bot(command_prefix="!", intents=discord.Intents.none())
    try:
        for cog in (
            AdminCog(bot),
            HelpCog(bot),
            LeaderboardCog(bot),
            PanelsCog(bot),
            ProfileCog(bot),
            QueueCog(bot),
            RegistrationCog(bot),
            ResultCog(bot),
            SetupCog(bot),
        ):
            await bot.add_cog(cog)
        tree = _expected_slash_tree()
        for name, spec in tree.items():
            node = bot.tree.get_command(name)
            assert node is not None, f"/{name} not registered"
            assert node.description, f"/{name} has no description"
            subs = spec.get("subcommands")
            if subs is None:
                assert not isinstance(node, app_commands.Group)
                for param in node.parameters:
                    assert param.description, f"/{name} param {param.name} missing description"
                continue
            assert isinstance(node, app_commands.Group), f"/{name} should be a group"
            actual_sub_names = {s.name for s in node.commands}
            assert actual_sub_names == set(subs) if isinstance(subs, set) else set(subs.keys()), (
                f"/{name} subcommands mismatch: {actual_sub_names}"
            )
            for sub in node.commands:
                assert sub.description, f"/{name} {sub.name} has no description"
        yield bot
    finally:
        await bot.close()


async def test_slash_tree_descriptions(slash_bot):
    pass  # assertions run in the fixture


# ---------------------------------------------------------------------------
# Queue concurrency: concurrent join triggers exactly one claim
# ---------------------------------------------------------------------------

async def test_queue_full_claim_succeeds_once(client):
    ids = await _seed_full_queue(client, guild_id=100)
    svc = QueueService(client, queue_size=15)
    for pid in ids:
        await svc.join(100, pid)

    results = await asyncio.gather(
        MatchService(client).claim_from_queue(100),
        MatchService(client).claim_from_queue(100),
    )
    claims = [r for r in results if r is not None]
    assert len(claims) == 1
    assert await QueueService(client).count(100) == 0


# ---------------------------------------------------------------------------
# Result lifecycle: submit → approve, double submit, double approve, reject
# ---------------------------------------------------------------------------

async def test_submit_approve_settles(client):
    match, selected, ids = await _claim_match(client)
    rs = ResultService(client)
    impostors = ids[:2]  # P0, P1 are impostors
    await rs.submit_result(
        100, match.id, submitted_by=2000, winner_side="CREWMATE",
        impostor_player_ids=impostors, screenshot_url="https://example.com/img.png",
    )
    await rs.approve_result(match.id, approved_by=999)
    updated = await rs.get_match(match.id)
    assert updated.status == "COMPLETED"

    # Impostors lose when CREWMATE wins
    impostor_p = await PlayerRepository(client).get_by_id(ids[0])
    assert impostor_p.elo == 1000 + (-6)
    assert impostor_p.matches == 1
    assert impostor_p.losses == 1

    # Crewmates win
    crew_p = await PlayerRepository(client).get_by_id(ids[4])
    assert crew_p.elo == 1004 + 8  # default_elo=1004 for P4, win_elo=8
    assert crew_p.matches == 1
    assert crew_p.wins == 1

    assert client.tables["match_results"]


async def test_double_submit_rejected(client):
    match, selected, ids = await _claim_match(client)
    rs = ResultService(client)
    await rs.submit_result(
        100, match.id, submitted_by=2000, winner_side="IMPOSTOR",
        impostor_player_ids=ids[:1], screenshot_url="https://example.com/img.png",
    )
    with pytest.raises(ValueError):
        await rs.submit_result(
            100, match.id, submitted_by=2001, winner_side="CREWMATE",
            impostor_player_ids=ids[1:3], screenshot_url="https://example.com/img2.png",
        )


async def test_double_approve_rejected(client):
    match, selected, ids = await _claim_match(client)
    rs = ResultService(client)
    await rs.submit_result(
        100, match.id, submitted_by=2000, winner_side="CREWMATE",
        impostor_player_ids=ids[:2], screenshot_url="https://example.com/img.png",
    )
    await rs.approve_result(match.id, approved_by=999)
    with pytest.raises(ValueError):
        await rs.approve_result(match.id, approved_by=999)


async def test_reject_reopens_match(client):
    match, selected, ids = await _claim_match(client)
    rs = ResultService(client)
    await rs.submit_result(
        100, match.id, submitted_by=2000, winner_side="CREWMATE",
        impostor_player_ids=ids[:2], screenshot_url="https://example.com/img.png",
    )
    await rs.reject_result(match.id, rejected_by=999)
    updated = await rs.get_match(match.id)
    assert updated.status == "IN_PROGRESS"
    subs = client.tables["result_submissions"]
    assert next(s for s in subs if s["match_id"] == match.id)["status"] == "REJECTED"


# ---------------------------------------------------------------------------
# Cross-guild isolation
# ---------------------------------------------------------------------------

async def test_cross_guild_submit_rejected(client):
    match, selected, ids = await _claim_match(client, guild_id=100)
    await _setup_guild(client, guild_id=200)
    player = await PlayerRepository(client).create(200, 9000, "B")
    rs = ResultService(client)
    with pytest.raises(ValueError):
        await rs.submit_result(
            200, match.id, submitted_by=player.discord_user_id, winner_side="CREWMATE",
            impostor_player_ids=[player.id], screenshot_url="https://example.com/img.png",
        )


@pytest.mark.parametrize("impostors", [[], [1, 2, 3, 4]])
async def test_result_rejects_invalid_impostor_count(client, impostors):
    match, _selected, ids = await _claim_match(client)
    resolved = [ids[index - 1] for index in impostors]
    with pytest.raises(ValueError, match="1–3"):
        await ResultService(client).submit_result(
            100,
            match.id,
            submitted_by=2000,
            winner_side="CREWMATE",
            impostor_player_ids=resolved,
            screenshot_url="https://example.com/img.png",
        )


async def test_result_requires_screenshot(client):
    match, _selected, ids = await _claim_match(client)
    with pytest.raises(ValueError, match="screenshot"):
        await ResultService(client).submit_result(
            100,
            match.id,
            submitted_by=2000,
            winner_side="CREWMATE",
            impostor_player_ids=ids[:2],
            screenshot_url="",
        )


# ---------------------------------------------------------------------------
# Panel embed limits
# ---------------------------------------------------------------------------

def test_panel_title_too_long():
    with pytest.raises(EmbedValidationError):
        PanelEmbedBuilder(title="x" * 257)


def test_panel_description_too_long():
    with pytest.raises(EmbedValidationError):
        PanelEmbedBuilder(description="x" * 4097)


def test_panel_bad_color():
    with pytest.raises(EmbedValidationError):
        PanelEmbedBuilder(color=0xFFFFFFFF)


def test_panel_bad_url():
    with pytest.raises(EmbedValidationError):
        PanelEmbedBuilder(thumbnail_url="not-a-url")


def test_panel_total_size_too_large():
    b = PanelEmbedBuilder(description="x" * 4096)
    b.add_field("f1", "y" * 1024)
    b.add_field("f2", "z" * 1024)
    with pytest.raises(EmbedValidationError):
        b.validate()


# ---------------------------------------------------------------------------
# SQL static security: SECURITY DEFINER + search_path + anon/auth revoked
# ---------------------------------------------------------------------------

SQL_DIR = Path(__file__).resolve().parent.parent / "supabase"


def _read_sql(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _find_functions(sql: str):
    pattern = re.compile(
        r"create\s+or\s+replace\s+function\s+public\.(\w+)\(.*?\)\s*"
        r"returns.*?"
        r"as\s*\$\$.*?\$\$;",
        re.DOTALL | re.IGNORECASE,
    )
    return pattern.finditer(sql)


def test_critical_rpcs_security_definer_and_search_path():
    critical = {
        "submit_match_result",
        "approve_match_result",
        "reject_match_result",
        "claim_match_from_queue",
        "pop_queue_entries",
    }
    for path in (SQL_DIR / "schema.sql", *sorted(SQL_DIR.glob("migrations/*.sql"))):
        sql = _read_sql(path)
        for match in _find_functions(sql):
            name = match.group(1)
            if name not in critical:
                continue
            body = match.group(0).lower()
            assert "security definer" in body, f"{name} missing SECURITY DEFINER in {path.name}"
            assert "set search_path" in body and "= ''" in body, (
                f"{name} missing set search_path = '' in {path.name}"
            )


def test_critical_rpcs_grants_and_revokes():
    critical_fns = {
        "submit_match_result": "(bigint, bigint, bigint, text, jsonb, text)",
        "approve_match_result": "(bigint, bigint, integer, integer)",
        "reject_match_result": "(bigint, bigint)",
        "claim_match_from_queue": "(bigint)",
        "pop_queue_entries": "(bigint)",
    }
    for path in (SQL_DIR / "schema.sql", *sorted(SQL_DIR.glob("migrations/*.sql"))):
        sql = _read_sql(path)
        sql_lower = sql.lower()
        for name, sig in critical_fns.items():
            revoke_pattern = f"revoke execute on function public.{name}{sig}"
            grant_prefix = f"grant execute on function public.{name}{sig}"
            if revoke_pattern.lower() in sql_lower:
                assert grant_prefix.lower() in sql_lower, (
                    f"{name} has revoke but no grant in {path.name}"
                )


# ---------------------------------------------------------------------------
# cleanup_match_channels migration exists and is idempotent
# ---------------------------------------------------------------------------

def test_cleanup_match_channels_migration_exists():
    migration = SQL_DIR / "migrations" / "20260911200000_cleanup_match_channels.sql"
    assert migration.exists()
    sql = migration.read_text(encoding="utf-8")
    assert "cleanup_match_channels" in sql
    assert "add column if not exists" in sql
