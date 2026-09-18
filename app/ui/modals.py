"""Modals for data entry."""

import discord

from app.logging import get_logger
from app.services.log_service import LogService
from app.services.registration_service import RegistrationService
from app.services.setup_service import SetupService
from app.supabase_client import get_client
from app.ui.base import LoggedModal

logger = get_logger(__name__)


class RegisterModal(LoggedModal, title="Among Us Registration"):
    among_us_name = discord.ui.TextInput(
        label="Among Us Name", placeholder="Your Among Us name...", required=True, max_length=32
    )
    nickname = discord.ui.TextInput(
        label="Nickname (optional)",
        placeholder="Optional nickname...",
        required=False,
        max_length=32,
    )
    faceit_nickname = discord.ui.TextInput(
        label="FACEIT Nickname (optional)",
        placeholder="FACEIT name...",
        required=False,
        max_length=32,
    )

    async def on_submit(self, interaction: discord.Interaction):
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
        if settings and settings.registered_role_id:
            role = interaction.guild.get_role(settings.registered_role_id)
            if role:
                await interaction.user.add_roles(role, reason="Registered")

        if settings and settings.nickname_format:
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

    async def _get_settings(self, interaction):
        return await SetupService(get_client()).get_settings(interaction.guild_id)
