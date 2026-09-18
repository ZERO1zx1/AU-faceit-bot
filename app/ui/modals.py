"""Modals for data entry."""

from __future__ import annotations

import discord

from app.logging import get_logger
from app.models.guild import GuildSettings
from app.services.log_service import LogService
from app.services.registration_service import RegistrationService
from app.services.setup_service import SetupService
from app.supabase_client import get_client
from app.ui.base import LoggedModal

logger = get_logger(__name__)


class RegisterModal(LoggedModal, title="Among Us Registration"):
    among_us_name: discord.ui.TextInput[discord.ui.View] = discord.ui.TextInput(
        label="Among Us Name", placeholder="Your Among Us name...", required=True, max_length=32
    )
    nickname: discord.ui.TextInput[discord.ui.View] = discord.ui.TextInput(
        label="Nickname (optional)",
        placeholder="Optional nickname...",
        required=False,
        max_length=32,
    )
    faceit_nickname: discord.ui.TextInput[discord.ui.View] = discord.ui.TextInput(
        label="FACEIT Nickname (optional)",
        placeholder="FACEIT name...",
        required=False,
        max_length=32,
    )

    async def on_submit(self, interaction: discord.Interaction) -> None:
        assert interaction.guild_id is not None
        name = self.among_us_name.value.strip()
        nick = self.nickname.value.strip() if self.nickname.value else None
        faceit_nick = self.faceit_nickname.value.strip() if self.faceit_nickname.value else None
        client = get_client()
        svc = RegistrationService(client)
        try:
            await svc.register(
                interaction.guild_id,
                interaction.user.id,
                name,
                nick,
                faceit_nickname=faceit_nick,
            )
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)
            return
        log_svc = LogService(client, interaction.client)
        await log_svc.log(
            interaction.guild_id,
            "REGISTER",
            actor_id=interaction.user.id,
            target_entity=name,
            details={"among_us_name": name, "nickname": nick},
        )

        settings = await self._get_settings(interaction)
        if (
            isinstance(interaction.user, discord.Member)
            and settings
            and settings.registered_role_id
            and interaction.guild is not None
        ):
            role = interaction.guild.get_role(settings.registered_role_id)
            if role:
                await interaction.user.add_roles(role, reason="Registered")

        if isinstance(interaction.user, discord.Member) and settings and settings.nickname_format:
            fmt = settings.nickname_format.replace("{name}", name).replace("{level}", "1")
            try:
                await interaction.user.edit(nick=fmt)
            except discord.HTTPException:
                logger.exception(
                    "Failed to apply registered nickname | guild_id=%s user_id=%s",
                    interaction.guild_id,
                    interaction.user.id,
                )

        await interaction.response.send_message(
            f"Амжилттай бүртгүүллээ! **{name}**", ephemeral=True
        )

    async def _get_settings(self, interaction: discord.Interaction) -> GuildSettings | None:
        if interaction.guild_id is None:
            return None
        return await SetupService(get_client()).get_settings(interaction.guild_id)


class RejectResultModal(LoggedModal, title="Reject Match Result"):
    """Admin/moderator rejection with an optional, auditable reason."""

    reason: discord.ui.TextInput[discord.ui.View] = discord.ui.TextInput(
        label="Reason (optional)",
        placeholder="Why is this result rejected?",
        required=False,
        max_length=200,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, match_id: int) -> None:
        super().__init__()
        self.match_id = match_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        from app.services.result_service import ResultService
        from app.ui.base import report_ui_error

        client = get_client()
        result_svc = ResultService(client)
        reason = self.reason.value.strip() if self.reason.value else None
        if interaction.guild is None:
            await interaction.response.send_message(
                "Энэ үйлдэл зөвхөн guild дотор хийгдэнэ.", ephemeral=True
            )
            return
        if not isinstance(interaction.user, discord.Member):
            await interaction.response.send_message(
                "Зөвхөн админ/модератор татгалзаж болно.", ephemeral=True
            )
            return
        from app.services.permission_service import PermissionService

        authorized = await PermissionService(client).is_moderator_member(interaction.user)
        if not authorized:
            await interaction.response.send_message(
                "Зөвхөн админ/модератор татгалзаж болно.", ephemeral=True
            )
            return
        assert interaction.guild_id is not None
        try:
            await result_svc.reject_result(
                self.match_id,
                rejected_by=interaction.user.id,
                guild_id=interaction.guild_id,
                reason=reason,
            )
        except ValueError as exc:
            await interaction.response.send_message(str(exc), ephemeral=True)
            return
        except Exception as exc:
            await report_ui_error(interaction, exc, component="result_reject")
            return

        log_svc = LogService(client, interaction.client)
        await log_svc.log(
            interaction.guild_id,
            "RESULT_REJECTED",
            actor_id=interaction.user.id,
            target_entity=str(self.match_id),
            details={"reason": reason} if reason else None,
        )
        await interaction.response.edit_message(content="Result rejected.", view=None)
