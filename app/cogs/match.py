"""Match cog — match creation, channel creation, CALL assignment."""

import asyncio
import contextlib

import discord
from discord.ext import commands

from app.logging import get_logger
from app.services.match_service import MatchService
from app.services.setup_service import SetupService
from app.supabase_client import get_client

logger = get_logger(__name__)


class MatchCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}

    async def create_match_channels(self, guild: discord.Guild, match, player_ids: list[int]):
        client = get_client()
        settings = await SetupService(client).get_settings(guild.id)
        if not settings or not settings.match_category_id:
            return None, None

        category = guild.get_channel(settings.match_category_id)
        if not category:
            return None, None

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            guild.me: discord.PermissionOverwrite(view_channel=True, manage_channels=True),
        }
        svc = MatchService(client)
        for player_id in player_ids:
            player = await svc.get_player(player_id)
            if not player or player.guild_id != guild.id:
                continue
            member = guild.get_member(player.discord_user_id)
            if member:
                overwrites[member] = discord.PermissionOverwrite(
                    view_channel=True, send_messages=True, connect=True, speak=True
                )

        text_ch = None
        voice_ch = None
        try:
            text_ch = await category.create_text_channel(
                f"au-{match.display_id.lower().replace('-', '')}", overwrites=overwrites
            )
            voice_ch = await category.create_voice_channel(
                f"AU-{match.display_id}", overwrites=overwrites
            )
            await svc.finalize_provisioning(match.id, text_ch.id, voice_ch.id)
        except Exception:
            for channel in (voice_ch, text_ch):
                if channel is not None:
                    with contextlib.suppress(discord.HTTPException):
                        await channel.delete(reason="Match channel setup failed")
            logger.exception("Match channel provisioning failed and was rolled back: %s", match.id)
            raise

        match_players = await svc.get_players(match.id)
        for mp in match_players:
            player = await svc.get_player(mp.player_id)
            if not player or player.guild_id != guild.id:
                continue
            member = guild.get_member(player.discord_user_id)
            if member:
                with contextlib.suppress(discord.HTTPException):
                    await member.move_to(voice_ch)
        return text_ch, voice_ch

    async def start_from_queue(self, guild: discord.Guild):
        """Claim a full queue and create its match atomically, then provision channels."""
        lock = self._locks.setdefault(guild.id, asyncio.Lock())
        async with lock:
            client = get_client()
            match_svc = MatchService(client)
            claimed = await match_svc.claim_from_queue(guild.id)
            if claimed is None:
                return
            match, selected = claimed
            try:
                text_ch, _voice_ch = await self.create_match_channels(guild, match, selected)
            except Exception:
                logger.exception("Match channel provisioning failed; requeueing: %s", match.id)
                text_ch = None

            if text_ch is None:
                await match_svc.requeue_players(match.id)
                return

            players = await match_svc.get_players(match.id)
            lines = []
            for mp in players:
                p = await match_svc.get_player(mp.player_id)
                name = p.among_us_name if p else f"Player #{mp.player_id}"
                lines.append(f"CALL {mp.call_number:02d} — {name}")
            embed = discord.Embed(
                title=f"━━━ MATCH {match.display_id} ━━━",
                description="**STATUS**\nIN PROGRESS\n\n**PLAYERS**\n\n" + "\n".join(lines),
                color=discord.Color.red(),
            )
            with contextlib.suppress(discord.HTTPException):
                await text_ch.send(embed=embed)


async def setup(bot):
    await bot.add_cog(MatchCog(bot))
