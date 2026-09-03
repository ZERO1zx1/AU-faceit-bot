"""Modals for data entry."""

import contextlib

import discord

from app.db import SessionFactory
from app.services.log_service import LogService
from app.services.registration_service import RegistrationService


class RegisterModal(discord.ui.Modal, title="Among Us Registration"):
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
        async with SessionFactory() as session:
            svc = RegistrationService(session)
            await svc.register(interaction.guild_id, interaction.user.id, name, nick)
            log_svc = LogService(session)
            await log_svc.log(
                interaction.guild_id, "REGISTER",
                actor_id=interaction.user.id, target_entity=name,
                details={"among_us_name": name, "nickname": nick},
            )
            await session.commit()

        settings = await self._get_settings(interaction)
        if settings and settings.registered_role_id:
            role = interaction.guild.get_role(settings.registered_role_id)
            if role:
                await interaction.user.add_roles(role, reason="Registered")

        if settings and settings.nickname_format:
            fmt = settings.nickname_format.replace("{name}", name).replace("{level}", "1")
            with contextlib.suppress(discord.HTTPException):
                await interaction.user.edit(nick=fmt)

        await interaction.response.send_message(
            f"Амжилттай бүртгүүллээ! **{name}**", ephemeral=True
        )

    async def _get_settings(self, interaction):
        async with SessionFactory() as session:
            from app.repositories.guild_repository import GuildRepository
            repo = GuildRepository(session)
            return await repo.get_settings(interaction.guild_id)
