import discord
from database import db

async def log_to_discord(bot, guild_id: int, embed: discord.Embed):
    settings = await db.get_guild_settings(guild_id)
    if settings and settings.get("log_channel_id"):
        channel = bot.get_channel(settings["log_channel_id"])
        if channel:
            try: await channel.send(embed=embed)
            except: pass
