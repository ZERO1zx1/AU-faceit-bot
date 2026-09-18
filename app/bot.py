"""AU FACEIT Bot — main entry point."""

import asyncio
import sys
import threading

import discord
from discord import app_commands
from discord.ext import commands

from app.config import settings
from app.logging import get_logger, setup_logging
from app.supabase_client import dispose_client, get_client, init_client

logger = get_logger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

COGS = [
    "app.cogs.setup",
    "app.cogs.registration",
    "app.cogs.profile",
    "app.cogs.faceit_level",
    "app.cogs.leaderboard",
    "app.cogs.queue",
    "app.cogs.match",
    "app.cogs.result",
    "app.cogs.voice",
    "app.cogs.panels",
    "app.cogs.admin",
    "app.cogs.help",
]

setup_logging()


def _exception_info(error: BaseException):
    return type(error), error, error.__traceback__


def _install_process_error_handlers() -> None:
    def process_exception(exc_type, exc_value, traceback):
        logger.critical(
            "Uncaught process exception",
            exc_info=(exc_type, exc_value, traceback),
        )

    def thread_exception(args: threading.ExceptHookArgs):
        logger.critical(
            "Uncaught thread exception | thread=%s",
            args.thread.name if args.thread else None,
            exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
        )

    sys.excepthook = process_exception
    threading.excepthook = thread_exception


_install_process_error_handlers()


class AUFaceitBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)
        self.leaderboard_task = None
        self._startup_recovery_done = False

    async def setup_hook(self):
        self.tree.on_error = self.on_app_command_error
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(self._on_asyncio_error)
        await init_client()
        for ext in COGS:
            try:
                await self.load_extension(ext)
                logger.debug("Loaded extension: %s", ext)
            except Exception as exc:
                logger.exception("Failed to load extension | extension=%s", ext)
                raise RuntimeError(f"Required extension failed to load: {ext}") from exc
        from app.ui.views import QueueView, RegisterView

        self.add_view(RegisterView())
        self.add_view(QueueView())
        logger.info("Persistent registration and queue views restored")
        await self._restore_result_views()

        from app.tasks.leaderboard_task import LeaderboardTask

        self.leaderboard_task = LeaderboardTask(self)
        await self.leaderboard_task.start()
        await self.tree.sync()
        logger.info("Slash commands synced")

    async def _restore_result_views(self) -> None:
        from app.services.result_service import ResultService
        from app.ui.views import ResultApprovalView

        submissions = await ResultService(get_client()).get_pending_submissions()
        restored = 0
        for submission in submissions:
            if submission.approval_message_id:
                self.add_view(
                    ResultApprovalView(submission.match_id),
                    message_id=submission.approval_message_id,
                )
                restored += 1
        logger.info("Persistent result approval views restored | count=%d", restored)

    def _on_asyncio_error(self, loop: asyncio.AbstractEventLoop, context: dict) -> None:
        error = context.get("exception")
        logger.error(
            "Unhandled asyncio error | message=%s future=%r task=%r",
            context.get("message"),
            context.get("future"),
            context.get("task"),
            exc_info=_exception_info(error) if error else None,
        )

    async def on_app_command_error(
        self,
        interaction: discord.Interaction,
        error: app_commands.AppCommandError,
    ) -> None:
        original = getattr(error, "original", error)
        command_name = interaction.command.qualified_name if interaction.command else None
        logger.error(
            "Slash command error | command=%s guild_id=%s channel_id=%s user_id=%s",
            command_name,
            interaction.guild_id,
            interaction.channel_id,
            interaction.user.id,
            exc_info=_exception_info(original),
        )
        message = "❌ Алдаа гарлаа. Админ `logs/cogs.txt` файлаас дэлгэрэнгүйг шалгана уу."
        try:
            if interaction.response.is_done():
                await interaction.followup.send(message, ephemeral=True)
            else:
                await interaction.response.send_message(message, ephemeral=True)
        except discord.HTTPException:
            logger.exception("Failed to send slash-command error response")

    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if ctx.command and ctx.command.has_error_handler():
            return
        original = getattr(error, "original", error)
        logger.error(
            "Prefix command error | command=%s guild_id=%s channel_id=%s user_id=%s",
            ctx.command.qualified_name if ctx.command else ctx.invoked_with,
            ctx.guild.id if ctx.guild else None,
            ctx.channel.id if ctx.channel else None,
            ctx.author.id,
            exc_info=_exception_info(original),
        )

    async def on_error(self, event_method: str, *args, **kwargs):
        logger.exception("Discord event error | event=%s", event_method)

    async def on_ready(self):
        logger.info("AU FACEIT Bot online as %s (ID: %s)", self.user, self.user.id)
        if not self._startup_recovery_done:
            await self._recover_sessions()
            self._startup_recovery_done = True

    async def _recover_sessions(self) -> None:
        """Restore/revert partially finished work left by a previous crash.

        - Voice: close open sessions older than the stale threshold.
        - Matches: matches stuck in CREATING are reverted and their players
          requeued; READY/IN_PROGRESS matches are left in place.
        """
        await self._close_stale_voice_sessions()
        await self._recover_creating_matches()

    async def _close_stale_voice_sessions(self) -> None:
        from app.services.voice_service import VoiceService

        try:
            closed = await VoiceService(get_client()).close_stale_sessions()
            logger.info("Voice recovery: closed stale sessions | count=%d", closed)
        except Exception:
            logger.exception("Voice recovery failed")

    async def _recover_creating_matches(self) -> None:
        from app.services.match_service import MatchService

        try:
            service = MatchService(get_client())
            active = await service.get_active_matches()
            recovered = 0
            for match in active:
                if match.guild_id not in self.guilds:
                    continue
                if match.status == "CREATING":
                    await service.requeue_players(match.id)
                    recovered += 1
            logger.info(
                "Match recovery: requeued CREATING matches | count=%d of %d active",
                recovered,
                len(active),
            )
        except Exception:
            logger.exception("Match recovery failed")

    async def close(self):
        if self.leaderboard_task is not None:
            await self.leaderboard_task.stop()
        await dispose_client()
        await super().close()


def main():
    bot = AUFaceitBot()
    try:
        bot.run(settings.discord_token, log_handler=None)
    except Exception:
        logger.exception("Fatal bot startup/runtime error")
        raise


if __name__ == "__main__":
    main()
