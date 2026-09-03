"""AU FACEIT Bot — main entry point."""

import os

import discord
from discord.ext import commands

from app.config import settings
from app.db import dispose_engine
from app.logging import get_logger, setup_logging

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
]

os.makedirs("logs", exist_ok=True)
setup_logging()


class AUFaceitBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        for ext in COGS:
            try:
                await self.load_extension(ext)
                logger.debug("Loaded extension: %s", ext)
            except Exception as e:
                logger.error("Failed to load %s: %s", ext, e)

    async def on_ready(self):
        logger.info("AU FACEIT Bot online as %s (ID: %s)", self.user, self.user.id)
        await self.tree.sync()
        logger.info("Slash commands synced")

    async def close(self):
        await dispose_engine()
        await super().close()


def main():
    bot = AUFaceitBot()
    bot.run(settings.discord_token, log_handler=None)


if __name__ == "__main__":
    main()
