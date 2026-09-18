"""Administrative slash commands for configuring a guild."""

import discord
from discord import app_commands
from discord.ext import commands

from app.logging import get_logger
from app.services.log_service import LogService
from app.services.queue_service import resolve_queue_size
from app.services.setup_service import SetupService
from app.supabase_client import get_client
from app.ui.embeds import queue_embed, registration_embed
from app.ui.views import QueueView, RegisterView

logger = get_logger(__name__)

DEFAULT_LEVEL_BOUNDARIES = {
    1: (0, 799),
    2: (800, 899),
    3: (900, 999),
    4: (1000, 1099),
    5: (1100, 1199),
    6: (1200, 1299),
    7: (1300, 1399),
    8: (1400, 1499),
    9: (1500, 1699),
    10: (1700, 999999),
}


def setup_embed(title: str, description: str, *, success: bool = True) -> discord.Embed:
    return discord.Embed(
        title=title,
        description=description,
        color=discord.Color.green() if success else discord.Color.red(),
    )


class SetupCog(commands.Cog):
    setup = app_commands.Group(
        name="setup",
        description="AU FACEIT серверийн тохиргоо болон panel-ууд.",
        guild_only=True,
        default_permissions=discord.Permissions(administrator=True),
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @setup.command(name="server", description="Үндсэн role болон match category-г бэлтгэх.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_server(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        client = get_client()
        svc = SetupService(client)
        await svc.upsert_settings(
            guild.id, default_elo=1000, win_elo=8, loss_elo=-6, queue_size=15
        )

        registered_role = discord.utils.get(guild.roles, name="AU Registered")
        if not registered_role:
            registered_role = await guild.create_role(
                name="AU Registered", color=discord.Color.green(), reason="AU FACEIT setup"
            )

        match_category = discord.utils.get(guild.categories, name="AU Matches")
        if not match_category:
            match_category = await guild.create_category("AU Matches", reason="AU FACEIT setup")

        await svc.upsert_settings(
            guild.id,
            registered_role_id=registered_role.id,
            match_category_id=match_category.id,
        )
        await LogService(client, self.bot).log(
            guild.id,
            "SETUP_SERVER",
            actor_id=interaction.user.id,
            details={
                "registered_role_id": registered_role.id,
                "match_category_id": match_category.id,
            },
        )
        await interaction.followup.send(
            embed=setup_embed(
                "✅ Server setup complete",
                f"**Registered role:** {registered_role.mention}\n"
                f"**Match category:** {match_category.name}\n\n"
                "Audit channel-ийг тусад нь `/setup logs` командаар сонгоно.",
            ),
            ephemeral=True,
        )

    @setup.command(
        name="logs", description="Server activity audit log очих Discord channel-ийг сонгох."
    )
    @app_commands.describe(channel="Register, queue, match, result log хүлээн авах text channel.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_logs(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        guild = interaction.guild
        if guild is None:
            return
        permissions = channel.permissions_for(guild.me)
        if not (permissions.view_channel and permissions.send_messages and permissions.embed_links):
            await interaction.response.send_message(
                embed=setup_embed(
                    "❌ Log channel тохируулсангүй",
                    "Bot-д View Channel, Send Messages, Embed Links permission хэрэгтэй.",
                    success=False,
                ),
                ephemeral=True,
            )
            return
        await SetupService(get_client()).upsert_settings(
            guild.id, log_channel_id=channel.id
        )
        await interaction.response.send_message(
            embed=setup_embed(
                "✅ Discord audit log тохирлоо",
                f"Server activity log: {channel.mention}\n"
                "Code error log нь тусдаа `logs/cogs.txt` файлд хадгалагдана.",
            ),
            ephemeral=True,
        )

    @setup.command(name="register", description="Register button бүхий public panel байрлуулах.")
    @app_commands.describe(channel="Panel байрлуулах channel; хоосон бол одоогийн channel.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_register(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.followup.send("Panel нь text channel-д байрлана.", ephemeral=True)
            return
        message = await target.send(embed=registration_embed(), view=RegisterView())
        await SetupService(get_client()).upsert_settings(
            guild.id,
            register_channel_id=target.id,
            register_message_id=message.id,
        )
        await interaction.followup.send(
            embed=setup_embed("✅ Register panel бэлэн", f"Panel: {message.jump_url}"),
            ephemeral=True,
        )

    @setup.command(name="levels", description="FACEIT Level 1–10 role болон Elo хязгаарыг бэлтгэх.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_levels(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        client = get_client()
        svc = SetupService(client)
        created = 0
        for level, (min_elo, max_elo) in DEFAULT_LEVEL_BOUNDARIES.items():
            role = discord.utils.get(guild.roles, name=f"Level {level}")
            if not role:
                role = await guild.create_role(
                    name=f"Level {level}", reason="AU FACEIT level setup"
                )
                created += 1
            await svc.set_level(
                guild.id,
                level,
                min_elo=min_elo,
                max_elo=max_elo,
                role_id=role.id,
            )
        await interaction.followup.send(
            embed=setup_embed(
                "✅ FACEIT levels тохирлоо",
                f"Level 1–10 бүрэн холбогдлоо. Шинээр үүссэн role: **{created}**",
            ),
            ephemeral=True,
        )

    @setup.command(
        name="queue", description="Join/Leave button бүхий public queue panel байрлуулах."
    )
    @app_commands.describe(channel="Panel байрлуулах channel; хоосон бол одоогийн channel.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_queue(
        self,
        interaction: discord.Interaction,
        channel: discord.TextChannel | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        target = channel or interaction.channel
        if not isinstance(target, discord.TextChannel):
            await interaction.followup.send("Panel нь text channel-д байрлана.", ephemeral=True)
            return
        client = get_client()
        settings = await SetupService(client).get_settings(guild.id)
        queue_size = resolve_queue_size(settings)
        message = await target.send(
            embed=queue_embed(count=0, max_size=queue_size), view=QueueView()
        )
        await SetupService(client).upsert_settings(
            guild.id,
            queue_channel_id=target.id,
            queue_message_id=message.id,
        )
        await interaction.followup.send(
            embed=setup_embed("✅ Queue panel бэлэн", f"Panel: {message.jump_url}"),
            ephemeral=True,
        )

    @setup.command(
        name="leaderboard", description="Автомат leaderboard байрлах channel-ийг сонгох."
    )
    @app_commands.describe(channel="Leaderboard нийтлэх text channel.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.checks.has_permissions(administrator=True)
    async def setup_leaderboard(
        self, interaction: discord.Interaction, channel: discord.TextChannel
    ) -> None:
        guild = interaction.guild
        if guild is None:
            return
        await SetupService(get_client()).upsert_settings(
            guild.id, leaderboard_channel_id=channel.id
        )
        await interaction.response.send_message(
            embed=setup_embed("✅ Leaderboard channel тохирлоо", channel.mention),
            ephemeral=True,
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(SetupCog(bot))
