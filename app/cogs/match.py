"""Match cog — match creation, channel creation, CALL assignment."""

import contextlib

import discord
from discord.ext import commands

from app.repositories.guild_repository import GuildRepository
from app.services.match_service import MatchService
from app.supabase_client import get_client


class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def create_match_channels(self, guild: discord.Guild, match, player_ids: list[int]):
        client = get_client()
        repo = GuildRepository(client)
        settings = await repo.get_settings(guild.id)
        if not settings or not settings.match_category_id:
            return

        category = guild.get_channel(settings.match_category_id)
        if not category:
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
        }
        for uid in player_ids:
            member = guild.get_member(uid)
            if member:
                overwrites[member] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, connect=True, speak=True
                )

        text_ch = await category.create_text_channel(
            f"au-{match.display_id.lower().replace('-', '')}", overwrites=overwrites
        )
        voice_ch = await category.create_voice_channel(
            f"AU-{match.display_id}", overwrites=overwrites
        )

        svc = MatchService(client)
        await svc.update_channels(match.id, text_ch.id, voice_ch.id)
        await svc.set_status(match.id, "READY")

        players = await svc.get_players(match.id)
        for p in players:
            member = guild.get_member(p.player_id)
            if member:
                with contextlib.suppress(discord.HTTPException):
                    await member.move_to(voice_ch)
        return text_ch, voice_ch


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
