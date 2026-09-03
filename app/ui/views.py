"""Persistent views for the bot."""

import discord

from app.db import SessionFactory
from app.services.queue_service import QueueService
from app.services.registration_service import RegistrationService
from app.utils.ids import BUTTON_IDS


class RegisterView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="REGISTER", style=discord.ButtonStyle.primary, custom_id=BUTTON_IDS["register"]
    )
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        from app.ui.modals import RegisterModal
        await interaction.response.send_modal(RegisterModal())


class QueueView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="ENTER MATCH", style=discord.ButtonStyle.success, custom_id=BUTTON_IDS["queue_join"]
    )
    async def join_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with SessionFactory() as session:
            svc = QueueService(session, queue_size=15)
            try:
                count = await svc.join(interaction.guild_id, interaction.user.id)
                await interaction.response.send_message(
                    f"Queue-д орлоо! ({count}/15)", ephemeral=True
                )
            except ValueError as e:
                await interaction.response.send_message(str(e), ephemeral=True)

    @discord.ui.button(
        label="LEAVE QUEUE", style=discord.ButtonStyle.danger, custom_id=BUTTON_IDS["queue_leave"]
    )
    async def leave_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with SessionFactory() as session:
            svc = QueueService(session, queue_size=15)
            await svc.leave(interaction.guild_id, interaction.user.id)
            await interaction.response.send_message("Queue-с гарлаа.", ephemeral=True)


class UnregisterConfirmView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)

    @discord.ui.button(
        label="CONFIRM",
        style=discord.ButtonStyle.danger,
        custom_id=BUTTON_IDS["unregister_confirm"],
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        async with SessionFactory() as session:
            svc = RegistrationService(session)
            await svc.unregister(interaction.guild_id, interaction.user.id)
            await session.commit()
            await interaction.response.edit_message(
                content="Бүртгэл устгагдлаа.", view=None
            )

    @discord.ui.button(
        label="CANCEL",
        style=discord.ButtonStyle.secondary,
        custom_id=BUTTON_IDS["unregister_cancel"],
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Цуцаллаа.", view=None)


class ResultApprovalView(discord.ui.View):
    def __init__(self, match_id: int):
        super().__init__(timeout=300)
        self.match_id = match_id

    @discord.ui.button(label="APPROVE", style=discord.ButtonStyle.success)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        from app.services.log_service import LogService
        from app.services.result_service import ResultService
        async with SessionFactory() as session:
            result_svc = ResultService(session)
            await result_svc.approve_result(self.match_id, approved_by=interaction.user.id)
            log_svc = LogService(session)
            await log_svc.log(
                interaction.guild_id, "RESULT_APPROVED",
                actor_id=interaction.user.id, target_entity=str(self.match_id),
            )
            await session.commit()
        await interaction.response.edit_message(content="Result approved!", view=None)

    @discord.ui.button(label="REJECT", style=discord.ButtonStyle.danger)
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Result rejected.", view=None)
