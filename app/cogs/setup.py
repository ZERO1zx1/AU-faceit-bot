"""Setup cog — server, register, level, queue and leaderboard setup commands."""

import discord
from discord.ext import commands
from sqlalchemy import select

from app.db import SessionFactory
from app.models.level import LevelRole
from app.repositories.guild_repository import GuildRepository

DEFAULT_LEVEL_BOUNDARIES = {
    1: (0, 799), 2: (800, 899), 3: (900, 999), 4: (1000, 1099),
    5: (1100, 1199), 6: (1200, 1299), 7: (1300, 1399), 8: (1400, 1499),
    9: (1500, 1699), 10: (1700, 999999),
}


class SetupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="setup-server")
    @commands.has_permissions(administrator=True)
    async def setup_server(self, ctx: commands.Context):
        guild = ctx.guild
        async with SessionFactory() as session:
            repo = GuildRepository(session)
            await repo.upsert_settings(
                guild.id,
                default_elo=1000,
                win_elo=8,
                loss_elo=-6,
                queue_size=15,
            )
            await session.commit()

        registered_role = discord.utils.get(guild.roles, name="AU Registered")
        if not registered_role:
            try:
                registered_role = await guild.create_role(
                    name="AU Registered", color=discord.Color.green()
                )
            except discord.HTTPException:
                return await ctx.send("Failed to create AU Registered role.")

        log_channel = discord.utils.get(guild.text_channels, name="au-bot-logs")
        if not log_channel:
            try:
                log_channel = await guild.create_text_channel("au-bot-logs")
            except discord.HTTPException:
                log_channel = None

        match_category = discord.utils.get(guild.categories, name="AU Matches")
        if not match_category:
            try:
                match_category = await guild.create_category("AU Matches")
            except discord.HTTPException:
                match_category = None

        async with SessionFactory() as session:
            repo = GuildRepository(session)
            await repo.upsert_settings(
                guild.id,
                registered_role_id=registered_role.id,
                log_channel_id=log_channel.id if log_channel else None,
                match_category_id=match_category.id if match_category else None,
            )
            await session.commit()

        await ctx.send(
            "✅ **SERVER SETUP COMPLETE**\n"
            f"🟢 Registered Role: {registered_role.mention}\n"
            f"📋 Log Channel: {log_channel.mention if log_channel else 'N/A'}\n"
            f"📁 Match Category: {match_category.name if match_category else 'N/A'}"
        )

    @commands.command(name="setup-register")
    @commands.has_permissions(administrator=True)
    async def setup_register(self, ctx: commands.Context):
        from app.ui.embeds import registration_embed
        from app.ui.views import RegisterView

        embed = registration_embed()
        view = RegisterView()
        msg = await ctx.send(embed=embed, view=view)
        async with SessionFactory() as session:
            repo = GuildRepository(session)
            await repo.upsert_settings(
                ctx.guild.id,
                register_channel_id=ctx.channel.id,
                register_message_id=msg.id,
            )
            await session.commit()
        await ctx.send("✅ Registration panel created!")

    @commands.command(name="setup-faceit-level")
    @commands.has_permissions(administrator=True)
    async def setup_levels(self, ctx: commands.Context):
        default_boundaries = DEFAULT_LEVEL_BOUNDARIES
        async with SessionFactory() as session:
            for level, (min_elo, max_elo) in default_boundaries.items():
                result = await session.execute(
                    select(LevelRole).where(
                        LevelRole.guild_id == ctx.guild.id, LevelRole.level == level
                    )
                )
                if result.scalar_one_or_none():
                    continue
                role = discord.utils.get(ctx.guild.roles, name=f"Level {level}")
                if not role:
                    try:
                        role = await ctx.guild.create_role(name=f"Level {level}")
                    except discord.HTTPException:
                        role = None
                lr = LevelRole(
                    guild_id=ctx.guild.id, level=level, min_elo=min_elo, max_elo=max_elo,
                    role_id=role.id if role else None,
                )
                session.add(lr)
            await session.commit()
        await ctx.send("✅ Level roles (1-10) configured!")

    @commands.command(name="setup-queue")
    @commands.has_permissions(administrator=True)
    async def setup_queue(self, ctx: commands.Context):
        from app.ui.embeds import queue_embed
        from app.ui.views import QueueView

        embed = queue_embed(count=0, max_size=15)
        view = QueueView()
        msg = await ctx.send(embed=embed, view=view)
        async with SessionFactory() as session:
            repo = GuildRepository(session)
            await repo.upsert_settings(
                ctx.guild.id,
                queue_channel_id=ctx.channel.id,
                queue_message_id=msg.id,
            )
            await session.commit()
        await ctx.send("✅ Queue panel created!")

    @commands.command(name="setup-leaderboard")
    @commands.has_permissions(administrator=True)
    async def setup_leaderboard(self, ctx: commands.Context):
        async with SessionFactory() as session:
            repo = GuildRepository(session)
            await repo.upsert_settings(ctx.guild.id, leaderboard_channel_id=ctx.channel.id)
            await session.commit()
        await ctx.send("✅ Leaderboard channel set! Use `/leaderboard` to post.")


async def setup(bot):
    await bot.add_cog(SetupCog(bot))
