import discord
from discord.ext import commands
from config import config
from database import db

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

class AUFaceitBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.setup")
        await self.load_extension("cogs.player")
        await self.load_extension("cogs.queue")
        await self.load_extension("cogs.match")
        await self.load_extension("cogs.leaderboard")
        await self.load_extension("cogs.panel")
        await self.load_extension("cogs.admin")
        await self.load_extension("cogs.voice")

    async def on_ready(self):
        print(f"🚀 AU FACEIT Bot online as {self.user}")

bot = AUFaceitBot(command_prefix=config.prefix, intents=intents)
bot.run(config.token)
