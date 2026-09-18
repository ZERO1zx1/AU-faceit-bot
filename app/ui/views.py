"""Persistent views for the bot.

Every component routes through the service layer — no direct repository or
Supabase access here — so button interactions behave identically to the slash
commands. Views with ``timeout=None`` and stable ``custom_id`` values are
restored after a restart with ``bot.add_view``.
"""

import contextlib

import discord

from app.logging import get_logger
from app.services.level_service import LevelService
from app.services.log_service import LogService
from app.services.permission_service import PermissionService
from app.services.player_service import PlayerService
from app.services.queue_service import QueueService
from app.services.registration_service import RegistrationService
from app.services.result_service import ResultService
from app.services.setup_service import SetupService
from app.supabase_client import get_client
from app.ui.base import LoggedView, report_ui_error
from app.ui.embeds import queue_embed
from app.utils.ids import BUTTON_IDS

logger = get_logger(__name__)


class RegisterView(LoggedView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="REGISTER", style=discord.ButtonStyle.primary, custom_id=BUTTON_IDS["register"]
    )
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        from app.ui.modals import RegisterModal

        await interaction.response.send_modal(RegisterModal())


async def _refresh_queue_panel(interaction: discord.Interaction, settings) -> None:
    """Edit the persisted queue embed with the current count and average Elo."""
    if not settings or not settings.queue_channel_id or not settings.queue_message_id:
        return
    channel = interaction.guild.get_channel(settings.queue_channel_id)
    if not channel:
        return
    try:
        message = await channel.fetch_message(settings.queue_message_id)
        svc = QueueService(get_client(), queue_size=settings.queue_size or 15)
        count, avg_elo = await svc.get_status(interaction.guild_id)
        await message.edit(embed=queue_embed(count, settings.queue_size or 15, avg_elo))
    except discord.HTTPException:
        pass


class QueueView(LoggedView):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ENTER MATCH", style=discord.ButtonStyle.success, custom_id=BUTTON_IDS["queue_join"]
    )
    async def join_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        client = get_client()
        setup_svc = SetupService(client)
        settings = await setup_svc.get_settings(interaction.guild_id)
        queue_size = settings.queue_size if settings else 15

        player_svc = PlayerService(client)
        player = await player_svc.get(interaction.guild_id, interaction.user.id)
        if not player or not player.active:
            await interaction.response.send_message(
                "Та эхлээд бүртгүүлнэ үү.", ephemeral=True
            )
            return

        svc = QueueService(client, queue_size=queue_size)
        try:
            count = await svc.join(interaction.guild_id, player.id)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return

        await interaction.response.send_message(
            f"Queue-д орлоо! ({count}/{queue_size})", ephemeral=True
        )
        await _refresh_queue_panel(interaction, settings)
        await LogService(client, interaction.client).log(
            interaction.guild_id,
            "QUEUE_JOIN",
            actor_id=interaction.user.id,
            target_entity=player.among_us_name,
            details={"position": count, "queue_size": queue_size},
        )

        if count >= queue_size:
            match_cog = interaction.client.get_cog("MatchCog")
            if match_cog:
                await match_cog.start_from_queue(interaction.guild)

    @discord.ui.button(
        label="LEAVE QUEUE", style=discord.ButtonStyle.danger, custom_id=BUTTON_IDS["queue_leave"]
    )
    async def leave_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        client = get_client()
        setup_svc = SetupService(client)
        settings = await setup_svc.get_settings(interaction.guild_id)
        queue_size = settings.queue_size if settings else 15

        player_svc = PlayerService(client)
        player = await player_svc.get(interaction.guild_id, interaction.user.id)
        if player:
            svc = QueueService(client, queue_size=queue_size)
            await svc.leave(interaction.guild_id, player.id)
            await LogService(client, interaction.client).log(
                interaction.guild_id,
                "QUEUE_LEAVE",
                actor_id=interaction.user.id,
                target_entity=player.among_us_name,
            )
        await interaction.response.send_message("Queue-с гарлаа.", ephemeral=True)
        await _refresh_queue_panel(interaction, settings)


class UnregisterConfirmView(LoggedView):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="CONFIRM",
        style=discord.ButtonStyle.danger,
        custom_id=BUTTON_IDS["unregister_confirm"],
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        client = get_client()
        svc = RegistrationService(client)
        try:
            await svc.unregister(interaction.guild_id, interaction.user.id)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        await LogService(client, interaction.client).log(
            interaction.guild_id,
            "UNREGISTER",
            actor_id=interaction.user.id,
            target_entity=str(interaction.user.id),
        )
        await interaction.response.edit_message(content="Бүртгэл устгагдлаа.", view=None)

    @discord.ui.button(
        label="CANCEL",
        style=discord.ButtonStyle.secondary,
        custom_id=BUTTON_IDS["unregister_cancel"],
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Цуцаллаа.", view=None)


class ResultApprovalView(LoggedView):
    def __init__(self, match_id: int):
        super().__init__(timeout=None)
        self.match_id = match_id
        self.approve.custom_id = f"au:result:approve:{match_id}"
        self.reject.custom_id = f"au:result:reject:{match_id}"

    async def _is_admin(self, interaction: discord.Interaction) -> bool:
        return await PermissionService(get_client()).is_admin_member(interaction.user)

    async def _sync_levels(self, interaction: discord.Interaction) -> None:
        client = get_client()
        result_svc = ResultService(client)
        level_svc = LevelService(client)
        players = await result_svc.get_match_players(self.match_id)
        for match_player in players:
            player = await result_svc.get_player_by_id(match_player.player_id)
            if not player or player.guild_id != interaction.guild_id:
                continue
            member = interaction.guild.get_member(player.discord_user_id)
            if member is None:
                continue
            changed = await level_svc.refresh_player_level(
                interaction.guild_id, player.id, member
            )
            if changed:
                await LogService(client, interaction.client).log(
                    interaction.guild_id,
                    "LEVEL_CHANGE",
                    actor_id=interaction.user.id,
                    target_entity=f"Level {changed[0]} \u2192 {changed[1]}",
                    details={"player_id": player.id},
                )

    @discord.ui.button(label="APPROVE", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_admin(interaction):
            await interaction.response.send_message(
                "Зөвхөн админ баталгаажуулж болно.", ephemeral=True
            )
            return

        client = get_client()
        result_svc = ResultService(client)
        try:
            await result_svc.approve_result(self.match_id, approved_by=interaction.user.id)
        except ValueError as e:
            await report_ui_error(interaction, e, component="result_approval")
            return

        log_svc = LogService(client, interaction.client)
        await log_svc.log(
            interaction.guild_id,
            "RESULT_APPROVED",
            actor_id=interaction.user.id,
            target_entity=str(self.match_id),
        )
        with contextlib.suppress(Exception):
            await self._sync_levels(interaction)
        await interaction.response.edit_message(content="Result approved!", view=None)
        await self._cleanup_channels(interaction)

    @discord.ui.button(label="REJECT", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._is_admin(interaction):
            await interaction.response.send_message("Зөвхөн админ татгалзаж болно.", ephemeral=True)
            return

        from app.services.result_service import ResultService

        client = get_client()
        result_svc = ResultService(client)
        try:
            await result_svc.reject_result(self.match_id, rejected_by=interaction.user.id)
        except ValueError as e:
            await report_ui_error(interaction, e, component="result_reject")
            return
        log_svc = LogService(client, interaction.client)
        await log_svc.log(
            interaction.guild_id,
            "RESULT_REJECTED",
            actor_id=interaction.user.id,
            target_entity=str(self.match_id),
        )
        await interaction.response.edit_message(content="Result rejected.", view=None)

    async def _cleanup_channels(self, interaction: discord.Interaction) -> None:
        """Delete the match channels after approval if the guild permits it."""
        try:
            client = get_client()
            settings = await SetupService(client).get_settings(interaction.guild_id)
            if settings and settings.cleanup_match_channels is False:
                return
            from app.services.match_service import MatchService

            match = await MatchService(client).get_match(self.match_id)
            if match is None:
                return
            guild = interaction.guild
            for channel_id in (match.text_channel_id, match.voice_channel_id):
                if not channel_id:
                    continue
                channel = guild.get_channel(channel_id)
                if channel is not None:
                    await channel.delete(reason="Match completed")
        except Exception as exc:
            logger.warning("Match channel cleanup failed: %s", exc)
