"""Slash commands for submitting and reviewing match results."""

import discord
from discord import app_commands
from discord.ext import commands

from app.services.result_service import ResultService
from app.supabase_client import get_client
from app.ui.embeds import match_result_embed
from app.ui.views import ResultApprovalView


class ResultCog(commands.Cog):
    result = app_commands.Group(
        name="result", description="Match result илгээх болон шалгах.", guild_only=True
    )

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @result.command(
        name="submit", description="Match result-ийг screenshot-той admin approval-д илгээх."
    )
    @app_commands.describe(
        match_id="Database дахь match ID.",
        winner="Ялсан тал.",
        screenshot="Тоглолтын үр дүнгийн зураг.",
        impostor_1="Эхний impostor.",
        impostor_2="Хоёр дахь impostor (байвал).",
        impostor_3="Гурав дахь impostor (байвал).",
    )
    @app_commands.choices(
        winner=[
            app_commands.Choice(name="Crewmate", value="CREWMATE"),
            app_commands.Choice(name="Impostor", value="IMPOSTOR"),
        ]
    )
    async def submit_result(
        self,
        interaction: discord.Interaction,
        match_id: int,
        winner: app_commands.Choice[str],
        screenshot: discord.Attachment,
        impostor_1: discord.Member,
        impostor_2: discord.Member | None = None,
        impostor_3: discord.Member | None = None,
    ) -> None:
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        if guild is None:
            return
        guild_id = guild.id
        if not screenshot.content_type or not screenshot.content_type.startswith("image/"):
            await interaction.followup.send("Screenshot нь image файл байх ёстой.", ephemeral=True)
            return

        client = get_client()
        service = ResultService(client)

        match = await service.get_match(match_id)
        if not match or match.guild_id != guild_id:
            await interaction.followup.send("Энэ серверт тохирох match олдсонгүй.", ephemeral=True)
            return
        if match.result_processed or match.status in ("COMPLETED", "RESULT_PENDING"):
            await interaction.followup.send(
                "Энэ match-ийн result аль хэдийн илгээгдсэн.", ephemeral=True
            )
            return

        match_players = await service.get_match_players(match_id)
        allowed_player_ids = {player.player_id for player in match_players}
        submitter = await service.get_player(guild_id, interaction.user.id)
        if not submitter or submitter.id not in allowed_player_ids:
            await interaction.followup.send(
                "Зөвхөн энэ match-д оролцсон тоглогч result илгээнэ.", ephemeral=True
            )
            return

        members = [member for member in (impostor_1, impostor_2, impostor_3) if member]
        if len({member.id for member in members}) != len(members):
            await interaction.followup.send(
                "Impostor тоглогч давхар сонгогдсон байна.", ephemeral=True
            )
            return
        impostor_ids: list[int] = []
        for member in members:
            player = await service.get_player(guild_id, member.id)
            if not player or player.id not in allowed_player_ids:
                await interaction.followup.send(
                    f"{member.mention} энэ match-ийн тоглогч биш байна.", ephemeral=True
                )
                return
            impostor_ids.append(player.id)

        submission = await service.submit_result(
            guild_id,
            match_id,
            submitted_by=interaction.user.id,
            winner_side=winner.value,
            impostor_player_ids=impostor_ids,
            screenshot_url=screenshot.url,
        )
        embed = discord.Embed(
            title=f"📋 Result approval — {match.display_id}",
            description=(
                f"**Winner:** {winner.name}\n"
                f"**Submitted by:** {interaction.user.mention}\n"
                f"**Impostors:** {', '.join(member.mention for member in members)}"
            ),
            color=discord.Color.orange(),
        )
        embed.set_image(url=screenshot.url)
        channel = interaction.channel
        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            await interaction.followup.send(
                "Result panel нь text channel-д илгээгдэнэ.", ephemeral=True
            )
            return
        message = await channel.send(embed=embed, view=ResultApprovalView(match_id))
        if submission.id:
            await service.set_approval_message(submission.id, message.id)
        await interaction.followup.send(
            f"✅ {match.display_id} result admin approval-д илгээгдлээ.", ephemeral=True
        )

    @result.command(
        name="review", description="Pending эсвэл боловсруулсан match result-ийг харах."
    )
    @app_commands.describe(match_id="Database дахь match ID.")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.checks.has_permissions(manage_guild=True)
    async def review_result(self, interaction: discord.Interaction, match_id: int) -> None:
        await interaction.response.defer(ephemeral=True)
        client = get_client()
        service = ResultService(client)
        match = await service.get_match(match_id)
        if not match or match.guild_id != interaction.guild_id:
            await interaction.followup.send("Match олдсонгүй.", ephemeral=True)
            return

        players = await service.get_match_players(match_id)
        results = []
        for match_player in players:
            player = await service.get_player_by_id(match_player.player_id)
            results.append(
                {
                    "name": player.among_us_name if player else str(match_player.player_id),
                    "role_side": match_player.role_side or "Unknown",
                    "elo_before": match_player.elo_before or 0,
                    "elo_after": match_player.elo_after or match_player.elo_before or 0,
                    "delta": match_player.elo_delta or 0,
                }
            )
        embed = match_result_embed(match, match.winner_side or "PENDING", results)
        if match.result_processed:
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(
                embed=embed, view=ResultApprovalView(match_id), ephemeral=True
            )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ResultCog(bot))
