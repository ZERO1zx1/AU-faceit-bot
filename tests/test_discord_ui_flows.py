"""Offline end-to-end tests for Discord UI interaction flows."""

from __future__ import annotations

from typing import Any, cast
from unittest.mock import patch

from app.repositories.guild_repository import GuildRepository
from app.repositories.player_repository import PlayerRepository
from app.ui.modals import RegisterModal
from app.ui.views import QueueView, UnregisterConfirmView
from tests.discord_mocks import interaction, set_text_input
from tests.fake_supabase import FakeSupabaseClient


async def test_register_modal_persists_player_and_acknowledges_interaction() -> None:
    client: Any = FakeSupabaseClient()
    await GuildRepository(client).upsert_settings(100, default_elo=1000, queue_size=15)
    modal = RegisterModal()
    set_text_input(modal, "among_us_name", "MockedPlayer")
    set_text_input(modal, "nickname", "Mock Nick")
    set_text_input(modal, "faceit_nickname", "faceit_mock")
    submitted = interaction(user_id=200)

    with patch("app.ui.modals.get_client", return_value=client):
        await modal.on_submit(cast(Any, submitted))

    player = await PlayerRepository(client).get(100, 200)
    assert player is not None
    assert player.among_us_name == "MockedPlayer"
    assert player.faceit_nickname == "faceit_mock"
    submitted.response.send_message.assert_awaited_once_with(
        "Амжилттай бүртгүүллээ! **MockedPlayer**", ephemeral=True
    )


async def test_queue_buttons_join_and_leave_use_persisted_state() -> None:
    client: Any = FakeSupabaseClient()
    await GuildRepository(client).upsert_settings(100, queue_size=2)
    player = await PlayerRepository(client).create(100, 200, "QueuePlayer")
    view = QueueView()
    joined = interaction(user_id=200)

    with patch("app.ui.views.get_client", return_value=client):
        await view.join_queue.callback(cast(Any, joined))

    assert await client.table("queue_entries").select("id").eq(
        "player_id", player.id
    ).execute()
    joined.response.send_message.assert_awaited_once_with("Queue-д орлоо! (1/2)", ephemeral=True)

    left = interaction(user_id=200)
    with patch("app.ui.views.get_client", return_value=client):
        await view.leave_queue.callback(cast(Any, left))

    remaining = await client.table("queue_entries").select("id").eq(
        "player_id", player.id
    ).execute()
    assert remaining.data == []
    left.response.send_message.assert_awaited_once_with("Queue-с гарлаа.", ephemeral=True)


async def test_unregister_confirmation_soft_deactivates_player() -> None:
    client: Any = FakeSupabaseClient()
    await GuildRepository(client).upsert_settings(100)
    player = await PlayerRepository(client).create(100, 200, "HistoryPlayer")
    view = UnregisterConfirmView()
    confirmed = interaction(user_id=200)

    with patch("app.ui.views.get_client", return_value=client):
        await view.confirm.callback(cast(Any, confirmed))

    assert player.id is not None
    updated = await PlayerRepository(client).get_by_id(player.id)
    assert updated is not None
    assert updated.active is False
    confirmed.response.edit_message.assert_awaited_once_with(
        content="Бүртгэл идэвхгүй боллоо.", view=None
    )
