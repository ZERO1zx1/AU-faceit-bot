"""Sync slash commands to the Discord API.

Usage: python -m scripts.sync_commands
"""

import asyncio

from app.bot import AUFaceitBot, setup_logging, COGS
from app.config import settings
from app.logging import get_logger

logger = get_logger(__name__)


async def sync() -> None:
    bot = AUFaceitBot()
    await bot.setup_hook()
    await bot.login(settings.discord_token)
    synced = await bot.tree.sync()
    logger.info("Synced %d commands", len(synced))
    await bot.close()


def main() -> None:
    asyncio.run(sync())


if __name__ == "__main__":
    main()
